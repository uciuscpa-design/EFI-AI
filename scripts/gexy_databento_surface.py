from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.core.config import get_settings
from packages.gexy.exposure import build_gex_surface, contract_exposure
from packages.gexy.greeks import enrich_missing_greeks
from packages.gexy.levels import rank_levels_by_unsigned_gex, summarize_gex_walls
from packages.gexy.models import OptionSurfacePoint, OptionType


NY = ZoneInfo("America/New_York")
DATASET = "OPRA.PILLAR"
SPX_MULTIPLIER = 100.0


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_clock(value: str) -> time:
    return time.fromisoformat(value)


def _fmt_money(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.3f}B"
    if magnitude >= 1_000_000:
        return f"${value / 1_000_000:,.3f}M"
    if magnitude >= 1_000:
        return f"${value / 1_000:,.3f}K"
    return f"${value:,.2f}"


def _load_chain_from_csv(path: Path, expiration: date) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"raw_symbol", "instrument_class", "strike_price", "open_interest"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"chain CSV missing required columns: {', '.join(missing)}")

    if "expiration" in frame.columns:
        parsed_expiration = pd.to_datetime(frame["expiration"], utc=True, errors="coerce")
        frame = frame.loc[parsed_expiration.dt.date == expiration].copy()

    frame = frame.dropna(subset=["raw_symbol", "instrument_class", "strike_price", "open_interest"])
    frame["instrument_class"] = frame["instrument_class"].astype(str).str.upper()
    frame = frame[frame["instrument_class"].isin(["C", "P"])].copy()
    return frame.drop_duplicates("raw_symbol", keep="last")


def _fetch_chain(client, trading_day: date, expiration: date, root: str, open_interest_stat) -> pd.DataFrame:
    parent = f"{root}.OPT"
    next_day = trading_day + timedelta(days=1)

    definitions = client.timeseries.get_range(
        dataset=DATASET,
        schema="definition",
        stype_in="parent",
        symbols=[parent],
        start=trading_day.isoformat(),
        end=next_day.isoformat(),
    ).to_df().reset_index()
    definitions = definitions.sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    definitions["expiration"] = pd.to_datetime(definitions["expiration"], utc=True, errors="coerce")
    definitions = definitions.loc[definitions["expiration"].dt.date == expiration].copy()

    oi_cutoff = datetime.combine(trading_day, time(9, 30), tzinfo=NY)
    stats = client.timeseries.get_range(
        dataset=DATASET,
        schema="statistics",
        stype_in="parent",
        symbols=[parent],
        start=trading_day.isoformat(),
        end=oi_cutoff.isoformat(),
    ).to_df().reset_index()
    stats = stats[stats["stat_type"] == open_interest_stat].sort_values("ts_recv")
    stats = stats.drop_duplicates("instrument_id", keep="last")
    oi = stats[["instrument_id", "quantity"]].rename(columns={"quantity": "open_interest"})

    chain = definitions.merge(oi, on="instrument_id", how="left")
    chain = chain.dropna(
        subset=["raw_symbol", "instrument_class", "strike_price", "open_interest"]
    ).copy()
    chain["instrument_class"] = chain["instrument_class"].astype(str).str.upper()
    chain = chain[chain["instrument_class"].isin(["C", "P"])]
    return chain.drop_duplicates("raw_symbol", keep="last")


def _fetch_exact_cbbo(client, chain: pd.DataFrame, quote_time: datetime) -> pd.DataFrame:
    symbols = chain["raw_symbol"].dropna().astype(str).unique().tolist()
    start = quote_time - timedelta(minutes=1)
    end = quote_time + timedelta(minutes=1)

    quotes = client.timeseries.get_range(
        dataset=DATASET,
        schema="cbbo-1m",
        stype_in="raw_symbol",
        symbols=symbols,
        start=start.isoformat(),
        end=end.isoformat(),
    ).to_df().reset_index()

    quotes["ts_recv"] = pd.to_datetime(quotes["ts_recv"], utc=True)
    target = pd.Timestamp(quote_time).tz_convert("UTC")
    quotes = quotes.loc[quotes["ts_recv"].dt.floor("min") == target].copy()
    quotes = quotes.sort_values("ts_recv").drop_duplicates("symbol", keep="last")
    quotes["mid_price"] = (quotes["bid_px_00"] + quotes["ask_px_00"]) / 2.0

    valid = (
        quotes["bid_px_00"].notna()
        & quotes["ask_px_00"].notna()
        & (quotes["bid_px_00"] >= 0)
        & (quotes["ask_px_00"] > 0)
        & (quotes["ask_px_00"] >= quotes["bid_px_00"])
    )
    quotes = quotes.loc[valid].copy()

    return quotes.merge(
        chain[["raw_symbol", "instrument_class", "strike_price", "open_interest"]],
        left_on="symbol",
        right_on="raw_symbol",
        how="inner",
    )


def _parity_forward(quotes: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    pairs = quotes.pivot_table(
        index="strike_price",
        columns="instrument_class",
        values="mid_price",
        aggfunc="last",
    )
    if "C" not in pairs.columns or "P" not in pairs.columns:
        raise ValueError("no matched call/put pairs at the requested CBBO minute")
    pairs = pairs.dropna(subset=["C", "P"]).copy()
    if pairs.empty:
        raise ValueError("no matched call/put pairs at the requested CBBO minute")

    # Zero-rate 0DTE approximation: C - P ~= F - K.
    pairs["implied_forward"] = pairs.index + pairs["C"] - pairs["P"]
    forward = float(pairs["implied_forward"].median())
    return forward, pairs


def _option_type(instrument_class: str) -> OptionType:
    return OptionType.CALL if instrument_class == "C" else OptionType.PUT


def _build_points(
    quotes: pd.DataFrame,
    *,
    expiration: date,
    open_interest_date: date,
    forward_proxy: float,
    time_to_expiry_years: float,
) -> tuple[list[OptionSurfacePoint], list[dict[str, object]]]:
    points: list[OptionSurfacePoint] = []
    rows: list[dict[str, object]] = []

    for row in quotes.itertuples(index=False):
        point = OptionSurfacePoint(
            symbol=str(row.raw_symbol),
            underlying_symbol="SPX",
            expiration_date=expiration,
            option_type=_option_type(str(row.instrument_class)),
            strike=float(row.strike_price),
            multiplier=SPX_MULTIPLIER,
            open_interest=float(row.open_interest),
            open_interest_date=open_interest_date,
            bid=float(row.bid_px_00),
            ask=float(row.ask_px_00),
            bid_size=float(row.bid_sz_00) if pd.notna(row.bid_sz_00) else None,
            ask_size=float(row.ask_sz_00) if pd.notna(row.ask_sz_00) else None,
            quote_timestamp=pd.Timestamp(row.ts_recv).to_pydatetime(),
        )
        enriched = enrich_missing_greeks(
            point,
            spot=forward_proxy,
            time_to_expiry_years=time_to_expiry_years,
            risk_free_rate=0.0,
            dividend_yield=0.0,
        )
        points.append(enriched.point)
        contribution = contract_exposure(enriched.point, forward_proxy)

        rows.append(
            {
                "symbol": enriched.point.symbol,
                "option_type": enriched.point.option_type.value,
                "strike": enriched.point.strike,
                "open_interest": enriched.point.open_interest,
                "bid": enriched.point.bid,
                "ask": enriched.point.ask,
                "mid": enriched.point.mid,
                "implied_volatility": enriched.implied_volatility,
                "gamma": enriched.point.gamma,
                "greek_source": enriched.source,
                "gax_notional_per_point": (
                    contribution.gax_notional_per_point if contribution else None
                ),
                "unsigned_gex_per_1pct": (
                    contribution.unsigned_gex_per_1pct if contribution else None
                ),
                "heuristic_signed_gex_per_1pct": (
                    contribution.heuristic_signed_gex_per_1pct if contribution else None
                ),
            }
        )

    return points, rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a first historical SPXW GEX/GAX surface from Databento OPRA."
    )
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument("--expiration", required=True, type=_parse_date)
    parser.add_argument("--quote-time", default=time(9, 35), type=_parse_clock)
    parser.add_argument("--root", default="SPXW")
    parser.add_argument(
        "--chain-csv",
        type=Path,
        help="Optional previously saved definition/OI chain; skips those Databento requests.",
    )
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    if args.top < 1:
        raise SystemExit("--top must be at least 1")

    quote_time = datetime.combine(args.trading_day, args.quote_time, tzinfo=NY)
    expiration_time = datetime.combine(args.expiration, time(16, 0), tzinfo=NY)
    if expiration_time <= quote_time:
        raise SystemExit("expiration must be after the requested quote time")

    time_to_expiry_years = (
        expiration_time - quote_time
    ).total_seconds() / (365.0 * 24.0 * 60.0 * 60.0)

    settings = get_settings()
    if not settings.databento_api_key:
        raise SystemExit(
            "DATABENTO_API_KEY was not found. Add it to the EFI-AI .env file; do not put it in source."
        )

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit(
            "databento is not installed. Run this script with: uv run --with databento python ..."
        ) from exc

    client = db.Historical(settings.databento_api_key)

    if args.chain_csv:
        chain = _load_chain_from_csv(args.chain_csv, args.expiration)
        chain_source = str(args.chain_csv)
    else:
        chain = _fetch_chain(
            client,
            args.trading_day,
            args.expiration,
            args.root,
            db.StatType.OPEN_INTEREST,
        )
        chain_source = "Databento definition + statistics"

    if chain.empty:
        raise SystemExit("no matching option contracts with open interest were found")

    quotes = _fetch_exact_cbbo(client, chain, quote_time)
    if quotes.empty:
        raise SystemExit("no valid CBBO records were found at the requested minute")

    forward_proxy, pairs = _parity_forward(quotes)
    points, contract_rows = _build_points(
        quotes,
        expiration=args.expiration,
        open_interest_date=args.trading_day,
        forward_proxy=forward_proxy,
        time_to_expiry_years=time_to_expiry_years,
    )

    surface = build_gex_surface(points, forward_proxy)
    walls = summarize_gex_walls(surface)
    ranked = rank_levels_by_unsigned_gex(surface, limit=args.top)

    stamp = f"{args.trading_day.isoformat()}_{args.quote_time.strftime('%H%M')}"
    contracts_path = Path(f"gexy_{args.root.lower()}_{stamp}_contracts.csv")
    levels_path = Path(f"gexy_{args.root.lower()}_{stamp}_levels.csv")
    pd.DataFrame(contract_rows).to_csv(contracts_path, index=False)
    pd.DataFrame(
        [
            {
                "strike": level.strike,
                "contracts": level.contracts,
                "gax_notional_per_point": level.gax_notional_per_point,
                "unsigned_gex_per_1pct": level.unsigned_gex_per_1pct,
                "heuristic_signed_gex_per_1pct": level.heuristic_signed_gex_per_1pct,
            }
            for level in surface.levels
        ]
    ).to_csv(levels_path, index=False)

    print(f"CHAIN SOURCE: {chain_source}")
    print(f"CHAIN CONTRACTS WITH OI: {len(chain)}")
    print(f"EXACT-MINUTE VALID CBBO: {len(quotes)}")
    print(f"CALL/PUT PAIRS: {len(pairs)}")
    print(f"PARITY SPX FORWARD PROXY: {forward_proxy:.3f}")
    print(
        "FORWARD RANGE (PAIR MIN/MAX): "
        f"{pairs['implied_forward'].min():.3f} / {pairs['implied_forward'].max():.3f}"
    )
    print(f"TIME TO 4:00 PM ET EXPIRY: {(expiration_time - quote_time)}")
    print(f"GREEKS SOLVED: {surface.contracts_used}")
    print(f"GREEKS UNAVAILABLE: {surface.contracts_missing_gamma}")
    print(f"TOTAL GAX / SPX POINT: {_fmt_money(surface.total_gax_notional_per_point)}")
    print(f"TOTAL UNSIGNED GEX / 1%: {_fmt_money(surface.total_unsigned_gex_per_1pct)}")
    print(
        "HEURISTIC SIGNED GEX / 1%: "
        f"{_fmt_money(surface.total_heuristic_signed_gex_per_1pct)}"
    )

    if walls.strongest_unsigned:
        print(f"STRONGEST UNSIGNED WALL: {walls.strongest_unsigned.strike:.1f}")
    if walls.strongest_positive_heuristic:
        print(
            "STRONGEST + HEURISTIC WALL: "
            f"{walls.strongest_positive_heuristic.strike:.1f}"
        )
    if walls.strongest_negative_heuristic:
        print(
            "STRONGEST - HEURISTIC WALL: "
            f"{walls.strongest_negative_heuristic.strike:.1f}"
        )

    print("\nTOP STRIKES BY UNSIGNED GEX")
    print("strike  contracts      unsigned_gex/1%       heuristic_signed_gex/1%")
    for level in ranked:
        print(
            f"{level.strike:7.1f} {level.contracts:10d} "
            f"{_fmt_money(level.unsigned_gex_per_1pct):>22} "
            f"{_fmt_money(level.heuristic_signed_gex_per_1pct):>28}"
        )

    print(f"\nSAVED CONTRACTS: {contracts_path}")
    print(f"SAVED LEVELS: {levels_path}")
    print(
        "NOTE: This first surface uses the put-call-parity forward as a spot proxy "
        "with a zero-rate 0DTE approximation. Call-positive / put-negative signed "
        "GEX is a structural heuristic, not observed dealer positioning."
    )


if __name__ == "__main__":
    main()
