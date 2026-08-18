from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, time
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

import pandas as pd

from packages.core.config import get_settings
from packages.gexy.exposure import build_gex_surface
from packages.gexy.forward_greeks import (
    black76_greeks,
    fit_forward_discount_from_parity,
    implied_volatility_from_forward_price,
)
from packages.gexy.levels import rank_levels_by_unsigned_gex, summarize_gex_walls
from packages.gexy.models import OptionSurfacePoint, OptionType
from packages.gexy.replay import add_change_features, add_forward_horizon_labels


NY = ZoneInfo("America/New_York")
DATASET = "OPRA.PILLAR"
SPX_MULTIPLIER = 100.0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def _parse_horizons(value: str) -> tuple[int, ...]:
    horizons = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    if not horizons or any(item < 1 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive comma-separated minutes")
    return horizons


def _option_type(value: str) -> OptionType:
    normalized = value.strip().upper()
    if normalized == "C":
        return OptionType.CALL
    if normalized == "P":
        return OptionType.PUT
    raise ValueError(f"unsupported option class: {value}")


def _load_chain(path: Path, expiration: date) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"raw_symbol", "instrument_class", "strike_price", "open_interest"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"chain CSV missing required columns: {', '.join(missing)}")

    if "expiration" in frame.columns:
        parsed = pd.to_datetime(frame["expiration"], utc=True, errors="coerce")
        frame = frame.loc[parsed.dt.date == expiration].copy()

    frame = frame.dropna(subset=list(required)).copy()
    frame["instrument_class"] = frame["instrument_class"].astype(str).str.upper()
    frame["strike_price"] = pd.to_numeric(frame["strike_price"], errors="coerce")
    frame["open_interest"] = pd.to_numeric(frame["open_interest"], errors="coerce")
    frame = frame.dropna(subset=["strike_price", "open_interest"])
    frame = frame[frame["instrument_class"].isin(["C", "P"])]
    return frame.drop_duplicates("raw_symbol", keep="last")


def _normalize_quotes(raw: pd.DataFrame, chain: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    if "ts_recv" not in frame.columns:
        frame = frame.reset_index()
    required = {"ts_recv", "symbol", "bid_px_00", "ask_px_00"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"CBBO data missing required columns: {', '.join(missing)}")

    frame["ts_recv"] = pd.to_datetime(frame["ts_recv"], utc=True, errors="coerce")
    for column in ("bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["ts_recv", "symbol", "bid_px_00", "ask_px_00"])
    frame = frame[
        (frame["bid_px_00"] >= 0)
        & (frame["ask_px_00"] > 0)
        & (frame["ask_px_00"] >= frame["bid_px_00"])
    ].copy()
    frame["mid_price"] = (frame["bid_px_00"] + frame["ask_px_00"]) / 2.0
    frame["minute"] = frame["ts_recv"].dt.floor("min")
    frame = frame.sort_values("ts_recv").drop_duplicates(["minute", "symbol"], keep="last")

    merge_columns = ["raw_symbol", "instrument_class", "strike_price", "open_interest"]
    merged = frame.merge(
        chain[merge_columns],
        left_on="symbol",
        right_on="raw_symbol",
        how="inner",
    )
    return merged.sort_values(["minute", "strike_price", "instrument_class"]).reset_index(drop=True)


def _fit_minute(group: pd.DataFrame):
    pivot = group.pivot_table(
        index="strike_price",
        columns="instrument_class",
        values="mid_price",
        aggfunc="last",
    )
    if "C" not in pivot.columns or "P" not in pivot.columns:
        return None, None
    pairs = pivot.dropna(subset=["C", "P"]).copy()
    if len(pairs) < 2:
        return None, pairs
    tuples = [
        (float(strike), float(row["C"]), float(row["P"]))
        for strike, row in pairs.iterrows()
    ]
    return fit_forward_discount_from_parity(tuples), pairs


def _surface_for_minute(
    group: pd.DataFrame,
    *,
    minute: pd.Timestamp,
    expiration: date,
    trading_day: date,
    expiration_time: datetime,
):
    fit, pairs = _fit_minute(group)
    if fit is None or pairs is None:
        return None

    quote_time = minute.tz_convert(NY).to_pydatetime()
    time_to_expiry_seconds = (expiration_time - quote_time).total_seconds()
    if time_to_expiry_seconds <= 0:
        return None
    time_to_expiry_years = time_to_expiry_seconds / (365.0 * 24.0 * 60.0 * 60.0)

    direct: dict[int, tuple[float, object]] = {}
    for index, row in group.iterrows():
        option_type = _option_type(str(row["instrument_class"]))
        iv = implied_volatility_from_forward_price(
            option_type=option_type,
            option_price=float(row["mid_price"]),
            forward=fit.forward,
            strike=float(row["strike_price"]),
            time_to_expiry_years=time_to_expiry_years,
            discount_factor=fit.discount_factor,
        )
        if iv is None:
            continue
        direct[index] = (
            iv,
            black76_greeks(
                option_type=option_type,
                forward=fit.forward,
                strike=float(row["strike_price"]),
                time_to_expiry_years=time_to_expiry_years,
                volatility=iv,
                discount_factor=fit.discount_factor,
            ),
        )

    otm_iv_by_strike: dict[float, float] = {}
    for index, (iv, _greeks) in direct.items():
        row = group.loc[index]
        strike = float(row["strike_price"])
        option_type = _option_type(str(row["instrument_class"]))
        is_otm = (
            option_type is OptionType.CALL and strike >= fit.forward
        ) or (
            option_type is OptionType.PUT and strike <= fit.forward
        )
        if is_otm:
            otm_iv_by_strike[strike] = iv

    points: list[OptionSurfacePoint] = []
    iv_rows: list[tuple[OptionType, float, float]] = []
    paired_recovered = 0

    for index, row in group.iterrows():
        option_type = _option_type(str(row["instrument_class"]))
        strike = float(row["strike_price"])
        solved = direct.get(index)
        if solved is None:
            paired_iv = otm_iv_by_strike.get(strike)
            if paired_iv is not None:
                paired_recovered += 1
                solved = (
                    paired_iv,
                    black76_greeks(
                        option_type=option_type,
                        forward=fit.forward,
                        strike=strike,
                        time_to_expiry_years=time_to_expiry_years,
                        volatility=paired_iv,
                        discount_factor=fit.discount_factor,
                    ),
                )

        point = OptionSurfacePoint(
            symbol=str(row["raw_symbol"]),
            underlying_symbol="SPX",
            expiration_date=expiration,
            option_type=option_type,
            strike=strike,
            multiplier=SPX_MULTIPLIER,
            open_interest=float(row["open_interest"]),
            open_interest_date=trading_day,
            bid=float(row["bid_px_00"]),
            ask=float(row["ask_px_00"]),
            bid_size=float(row["bid_sz_00"]) if "bid_sz_00" in row and pd.notna(row["bid_sz_00"]) else None,
            ask_size=float(row["ask_sz_00"]) if "ask_sz_00" in row and pd.notna(row["ask_sz_00"]) else None,
            quote_timestamp=pd.Timestamp(row["ts_recv"]).to_pydatetime(),
        )
        if solved is not None:
            iv, greeks = solved
            point = replace(
                point,
                implied_volatility=iv,
                delta=greeks.delta_forward,
                gamma=greeks.gamma_forward,
                vega=greeks.vega_per_vol_unit,
            )
            iv_rows.append((option_type, strike, iv))
        points.append(point)

    surface = build_gex_surface(points, fit.forward)
    walls = summarize_gex_walls(surface)
    ranked = rank_levels_by_unsigned_gex(surface, max(5, len(surface.levels)))

    total_unsigned = surface.total_unsigned_gex_per_1pct
    top1_concentration = (
        ranked[0].unsigned_gex_per_1pct / total_unsigned if ranked and total_unsigned > 0 else None
    )
    top5_concentration = (
        sum(level.unsigned_gex_per_1pct for level in ranked[:5]) / total_unsigned
        if ranked and total_unsigned > 0
        else None
    )

    all_ivs = [iv for _kind, _strike, iv in iv_rows]
    near_put_ivs = [
        iv
        for kind, strike, iv in iv_rows
        if kind is OptionType.PUT and fit.forward - 100.0 <= strike <= fit.forward
    ]
    near_call_ivs = [
        iv
        for kind, strike, iv in iv_rows
        if kind is OptionType.CALL and fit.forward <= strike <= fit.forward + 100.0
    ]
    near_put_iv = median(near_put_ivs) if near_put_ivs else None
    near_call_iv = median(near_call_ivs) if near_call_ivs else None
    near_iv_skew = (
        near_put_iv - near_call_iv
        if near_put_iv is not None and near_call_iv is not None
        else None
    )

    return {
        "timestamp": minute,
        "valid_quotes": len(group),
        "parity_pairs": fit.pair_count,
        "forward": fit.forward,
        "discount_factor_fit": fit.discount_factor,
        "parity_median_abs_residual": fit.median_abs_residual,
        "parity_max_abs_residual": fit.max_abs_residual,
        "time_to_expiry_minutes": time_to_expiry_seconds / 60.0,
        "greeks_direct": len(direct),
        "greeks_paired_recovered": paired_recovered,
        "greeks_solved": surface.contracts_used,
        "greeks_unavailable": surface.contracts_missing_gamma,
        "greeks_solved_pct": surface.contracts_used / len(points) if points else None,
        "median_implied_volatility": median(all_ivs) if all_ivs else None,
        "near_put_iv_100pt": near_put_iv,
        "near_call_iv_100pt": near_call_iv,
        "near_iv_skew_put_minus_call": near_iv_skew,
        "total_gax_forward_proxy_per_point": surface.total_gax_notional_per_point,
        "total_unsigned_gex_forward_proxy_per_1pct": surface.total_unsigned_gex_per_1pct,
        "heuristic_signed_gex_forward_proxy_per_1pct": surface.total_heuristic_signed_gex_per_1pct,
        "strongest_unsigned_wall": walls.strongest_unsigned.strike if walls.strongest_unsigned else None,
        "strongest_positive_heuristic_wall": (
            walls.strongest_positive_heuristic.strike
            if walls.strongest_positive_heuristic
            else None
        ),
        "strongest_negative_heuristic_wall": (
            walls.strongest_negative_heuristic.strike
            if walls.strongest_negative_heuristic
            else None
        ),
        "distance_to_unsigned_wall": (
            walls.strongest_unsigned.strike - fit.forward if walls.strongest_unsigned else None
        ),
        "distance_to_positive_wall": (
            walls.strongest_positive_heuristic.strike - fit.forward
            if walls.strongest_positive_heuristic
            else None
        ),
        "distance_to_negative_wall": (
            walls.strongest_negative_heuristic.strike - fit.forward
            if walls.strongest_negative_heuristic
            else None
        ),
        "top1_unsigned_gex_concentration": top1_concentration,
        "top5_unsigned_gex_concentration": top5_concentration,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a historical SPXW 0DTE GEXY surface minute-by-minute from Databento CBBO-1m."
    )
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument("--expiration", required=True, type=_parse_date)
    parser.add_argument("--chain-csv", required=True, type=Path)
    parser.add_argument("--start", default=time(9, 30), type=_parse_clock)
    parser.add_argument("--end", default=time(16, 0), type=_parse_clock)
    parser.add_argument("--horizons", default=(1, 5, 15, 30, 60), type=_parse_horizons)
    parser.add_argument("--quotes-csv", type=Path, help="Reuse a previously cached CBBO-1m CSV.")
    parser.add_argument("--cost-only", action="store_true")
    parser.add_argument("--min-parity-pairs", type=int, default=5)
    args = parser.parse_args()

    if args.expiration < args.trading_day:
        raise SystemExit("expiration cannot be before trading day")
    if args.min_parity_pairs < 2:
        raise SystemExit("--min-parity-pairs must be at least 2")

    start_time = datetime.combine(args.trading_day, args.start, tzinfo=NY)
    end_time = datetime.combine(args.trading_day, args.end, tzinfo=NY)
    expiration_time = datetime.combine(args.expiration, time(16, 0), tzinfo=NY)
    if end_time <= start_time:
        raise SystemExit("--end must be after --start")

    chain = _load_chain(args.chain_csv, args.expiration)
    if chain.empty:
        raise SystemExit("chain CSV contains no matching option contracts")
    symbols = chain["raw_symbol"].dropna().astype(str).unique().tolist()

    settings = get_settings()
    if not settings.databento_api_key and args.quotes_csv is None:
        raise SystemExit("DATABENTO_API_KEY was not found in .env")

    if args.quotes_csv is None:
        try:
            import databento as db
        except ImportError as exc:
            raise SystemExit(
                "databento is not installed. Run with: uv run --with databento --with pandas python ..."
            ) from exc
        client = db.Historical(settings.databento_api_key)
        if args.cost_only:
            cost = client.metadata.get_cost(
                dataset=DATASET,
                schema="cbbo-1m",
                stype_in="raw_symbol",
                symbols=symbols,
                start=start_time.isoformat(),
                end=end_time.isoformat(),
            )
            print(f"0DTE SYMBOLS: {len(symbols)}")
            print(f"REPLAY WINDOW: {start_time.isoformat()} -> {end_time.isoformat()}")
            print(f"FULL-DAY CBBO-1m COST: ${cost:.6f}")
            print("NO MARKET DATA DOWNLOADED")
            return

        raw = client.timeseries.get_range(
            dataset=DATASET,
            schema="cbbo-1m",
            stype_in="raw_symbol",
            symbols=symbols,
            start=start_time.isoformat(),
            end=end_time.isoformat(),
        ).to_df().reset_index()
        normalized = _normalize_quotes(raw, chain)
        quotes_path = Path(
            f"gexy_spxw_{args.trading_day.isoformat()}_{args.start.strftime('%H%M')}_{args.end.strftime('%H%M')}_cbbo_1m.csv"
        )
        normalized.to_csv(quotes_path, index=False)
        print(f"CACHED QUOTES: {quotes_path}")
    else:
        cached = pd.read_csv(args.quotes_csv)
        if {"instrument_class", "strike_price", "open_interest", "minute"}.issubset(cached.columns):
            normalized = cached.copy()
            normalized["ts_recv"] = pd.to_datetime(normalized["ts_recv"], utc=True, errors="coerce")
            normalized["minute"] = pd.to_datetime(normalized["minute"], utc=True, errors="coerce")
        else:
            normalized = _normalize_quotes(cached, chain)
        quotes_path = args.quotes_csv

    rows: list[dict[str, object]] = []
    skipped_low_pairs = 0
    for minute, group in normalized.groupby("minute", sort=True):
        minute_timestamp = pd.Timestamp(minute)
        fit, pairs = _fit_minute(group)
        if fit is None or pairs is None or len(pairs) < args.min_parity_pairs:
            skipped_low_pairs += 1
            continue
        row = _surface_for_minute(
            group,
            minute=minute_timestamp,
            expiration=args.expiration,
            trading_day=args.trading_day,
            expiration_time=expiration_time,
        )
        if row is not None:
            rows.append(row)

    if not rows:
        raise SystemExit("no replay minutes had enough parity pairs to build a surface")

    features = pd.DataFrame(rows)
    features = add_change_features(features)
    features = add_forward_horizon_labels(features, args.horizons)

    feature_path = Path(f"gexy_spxw_{args.trading_day.isoformat()}_replay_features.csv")
    features.to_csv(feature_path, index=False)

    first = features.iloc[0]
    last = features.iloc[-1]
    print(f"INPUT CONTRACTS: {len(chain)}")
    print(f"CACHED QUOTE ROWS: {len(normalized)}")
    print(f"REPLAY MINUTES BUILT: {len(features)}")
    print(f"MINUTES SKIPPED FOR LOW PARITY PAIRS: {skipped_low_pairs}")
    print(f"FIRST FORWARD: {first['forward']:.3f}")
    print(f"LAST FORWARD: {last['forward']:.3f}")
    print(f"MEDIAN PARITY PAIRS: {features['parity_pairs'].median():.1f}")
    print(f"MEDIAN GREEKS SOLVED: {features['greeks_solved'].median():.1f}")
    print(f"MEDIAN GREEKS SOLVED %: {features['greeks_solved_pct'].median():.1%}")
    print(f"FIRST UNSIGNED WALL: {first['strongest_unsigned_wall']:.1f}")
    print(f"LAST UNSIGNED WALL: {last['strongest_unsigned_wall']:.1f}")
    print(f"FIRST NEGATIVE HEURISTIC WALL: {first['strongest_negative_heuristic_wall']:.1f}")
    print(f"LAST NEGATIVE HEURISTIC WALL: {last['strongest_negative_heuristic_wall']:.1f}")
    print(f"HORIZON LABELS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"QUOTES SOURCE: {quotes_path}")
    print(f"SAVED FEATURES: {feature_path}")
    print("\nSAMPLE FEATURE ROWS")
    columns = [
        "timestamp",
        "forward",
        "total_unsigned_gex_forward_proxy_per_1pct",
        "heuristic_signed_gex_forward_proxy_per_1pct",
        "strongest_unsigned_wall",
        "strongest_negative_heuristic_wall",
        "d_forward",
        "d_total_unsigned_gex_forward_proxy_per_1pct",
        "forward_return_5m_bps",
        "forward_return_15m_bps",
    ]
    available = [column for column in columns if column in features.columns]
    print(features[available].head(10).to_string(index=False))
    print(
        "\nNOTE: Replay uses parity-fitted Black-76 forward gamma. Discount factor is a numerical "
        "parity-fit parameter, not an interest-rate forecast. Signed GEX remains the transparent "
        "call-positive / put-negative structural heuristic. Future labels use exact clock minutes."
    )


if __name__ == "__main__":
    main()
