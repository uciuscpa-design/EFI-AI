from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, time
from math import log
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.gexy.exposure import build_gex_surface
from packages.gexy.forward_greeks import (
    black76_greeks,
    fit_forward_discount_from_parity,
    implied_volatility_from_forward_price,
)
from packages.gexy.levels import rank_levels_by_unsigned_gex, summarize_gex_walls
from packages.gexy.models import OptionSurfacePoint, OptionType


NY = ZoneInfo("America/New_York")
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


def _option_type(value: str) -> OptionType:
    normalized = value.strip().lower()
    if normalized in {"c", "call"}:
        return OptionType.CALL
    if normalized in {"p", "put"}:
        return OptionType.PUT
    raise ValueError(f"unsupported option type: {value}")


def _load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"symbol", "option_type", "strike", "open_interest", "bid", "ask"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"contracts CSV missing required columns: {', '.join(missing)}")

    frame = frame.dropna(subset=list(required)).copy()
    frame["strike"] = pd.to_numeric(frame["strike"], errors="coerce")
    frame["open_interest"] = pd.to_numeric(frame["open_interest"], errors="coerce")
    frame["bid"] = pd.to_numeric(frame["bid"], errors="coerce")
    frame["ask"] = pd.to_numeric(frame["ask"], errors="coerce")
    frame = frame.dropna(subset=["strike", "open_interest", "bid", "ask"])
    frame = frame[(frame["bid"] >= 0) & (frame["ask"] > 0) & (frame["ask"] >= frame["bid"])].copy()
    frame["mid"] = (frame["bid"] + frame["ask"]) / 2.0
    return frame


def _fit_parity(frame: pd.DataFrame):
    pivot = frame.pivot_table(index="strike", columns="option_type", values="mid", aggfunc="last")
    call_col = "call" if "call" in pivot.columns else "C" if "C" in pivot.columns else None
    put_col = "put" if "put" in pivot.columns else "P" if "P" in pivot.columns else None
    if call_col is None or put_col is None:
        raise ValueError("contracts CSV does not contain matched call/put pairs")
    pairs = pivot.dropna(subset=[call_col, put_col]).copy()
    tuples = [
        (float(strike), float(row[call_col]), float(row[put_col]))
        for strike, row in pairs.iterrows()
    ]
    return fit_forward_discount_from_parity(tuples), pairs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild a saved SPXW surface with a parity-fitted Black-76 forward model."
    )
    parser.add_argument("--contracts-csv", required=True, type=Path)
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument("--expiration", required=True, type=_parse_date)
    parser.add_argument("--quote-time", required=True, type=_parse_clock)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    quote_time = datetime.combine(args.trading_day, args.quote_time, tzinfo=NY)
    expiration_time = datetime.combine(args.expiration, time(16, 0), tzinfo=NY)
    if expiration_time <= quote_time:
        raise SystemExit("expiration must be after quote time")
    time_to_expiry_years = (expiration_time - quote_time).total_seconds() / (365.0 * 24 * 60 * 60)

    frame = _load(args.contracts_csv)
    fit, pairs = _fit_parity(frame)

    direct: dict[int, tuple[float, object]] = {}
    for index, row in frame.iterrows():
        option_type = _option_type(str(row["option_type"]))
        iv = implied_volatility_from_forward_price(
            option_type=option_type,
            option_price=float(row["mid"]),
            forward=fit.forward,
            strike=float(row["strike"]),
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
                strike=float(row["strike"]),
                time_to_expiry_years=time_to_expiry_years,
                volatility=iv,
                discount_factor=fit.discount_factor,
            ),
        )

    # Prefer the directly solved OTM leg as the same-strike volatility fallback.
    otm_iv_by_strike: dict[float, float] = {}
    for index, (iv, _greeks) in direct.items():
        row = frame.loc[index]
        strike = float(row["strike"])
        option_type = _option_type(str(row["option_type"]))
        is_otm = (
            option_type is OptionType.CALL and strike >= fit.forward
        ) or (
            option_type is OptionType.PUT and strike <= fit.forward
        )
        if is_otm:
            otm_iv_by_strike[strike] = iv

    points: list[OptionSurfacePoint] = []
    rows: list[dict[str, object]] = []
    paired_recovered = 0

    for index, row in frame.iterrows():
        option_type = _option_type(str(row["option_type"]))
        strike = float(row["strike"])
        source = "black76_quote_iv"
        solved = direct.get(index)
        if solved is None:
            paired_iv = otm_iv_by_strike.get(strike)
            if paired_iv is not None:
                source = "black76_paired_otm_iv"
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
            symbol=str(row["symbol"]),
            underlying_symbol="SPX",
            expiration_date=args.expiration,
            option_type=option_type,
            strike=strike,
            multiplier=SPX_MULTIPLIER,
            open_interest=float(row["open_interest"]),
            open_interest_date=args.trading_day,
            bid=float(row["bid"]),
            ask=float(row["ask"]),
        )
        iv = None
        if solved is not None:
            iv, greeks = solved
            point = replace(
                point,
                implied_volatility=iv,
                delta=greeks.delta_forward,
                gamma=greeks.gamma_forward,
                vega=greeks.vega_per_vol_unit,
            )
        else:
            source = "unavailable"

        points.append(point)
        rows.append(
            {
                "symbol": point.symbol,
                "option_type": point.option_type.value,
                "strike": point.strike,
                "open_interest": point.open_interest,
                "bid": point.bid,
                "ask": point.ask,
                "mid": point.mid,
                "implied_volatility": iv,
                "gamma_forward": point.gamma,
                "greek_source": source,
            }
        )

    surface = build_gex_surface(points, fit.forward)
    walls = summarize_gex_walls(surface)
    ranked = rank_levels_by_unsigned_gex(surface, args.top)

    annualized_discount_rate = -log(fit.discount_factor) / time_to_expiry_years

    output_contracts = args.contracts_csv.with_name(args.contracts_csv.stem + "_black76.csv")
    output_levels = args.contracts_csv.with_name(args.contracts_csv.stem + "_black76_levels.csv")
    pd.DataFrame(rows).to_csv(output_contracts, index=False)
    pd.DataFrame(
        [
            {
                "strike": level.strike,
                "contracts": level.contracts,
                "gax_forward_proxy_per_point": level.gax_notional_per_point,
                "unsigned_gex_forward_proxy_per_1pct": level.unsigned_gex_per_1pct,
                "heuristic_signed_gex_forward_proxy_per_1pct": level.heuristic_signed_gex_per_1pct,
            }
            for level in surface.levels
        ]
    ).to_csv(output_levels, index=False)

    print(f"INPUT CONTRACTS: {len(frame)}")
    print(f"PARITY PAIRS: {fit.pair_count}")
    print(f"FITTED FORWARD: {fit.forward:.6f}")
    print(f"FITTED DISCOUNT FACTOR: {fit.discount_factor:.9f}")
    print(f"PARITY MEDIAN ABS RESIDUAL: {fit.median_abs_residual:.6f}")
    print(f"PARITY MAX ABS RESIDUAL: {fit.max_abs_residual:.6f}")
    print(f"ANNUALIZED RATE IMPLIED BY DISCOUNT: {annualized_discount_rate:.6%}")
    print(f"BLACK76 DIRECT GREEKS SOLVED: {len(direct)}")
    print(f"PAIRED OTM IV RECOVERED: {paired_recovered}")
    print(f"GREEKS SOLVED AFTER FALLBACK: {surface.contracts_used}")
    print(f"GREEKS UNAVAILABLE: {surface.contracts_missing_gamma}")
    print(f"TOTAL GAX FORWARD PROXY / POINT: {_fmt_money(surface.total_gax_notional_per_point)}")
    print(f"TOTAL UNSIGNED GEX FORWARD PROXY / 1%: {_fmt_money(surface.total_unsigned_gex_per_1pct)}")
    print(f"HEURISTIC SIGNED GEX FORWARD PROXY / 1%: {_fmt_money(surface.total_heuristic_signed_gex_per_1pct)}")

    if walls.strongest_unsigned:
        print(f"STRONGEST UNSIGNED WALL: {walls.strongest_unsigned.strike:.1f}")
    if walls.strongest_positive_heuristic:
        print(f"STRONGEST + HEURISTIC WALL: {walls.strongest_positive_heuristic.strike:.1f}")
    if walls.strongest_negative_heuristic:
        print(f"STRONGEST - HEURISTIC WALL: {walls.strongest_negative_heuristic.strike:.1f}")

    print("\nTOP STRIKES BY UNSIGNED FORWARD-GEX PROXY")
    print("strike  contracts      unsigned_gex/1%       heuristic_signed_gex/1%")
    for level in ranked:
        print(
            f"{level.strike:7.1f} {level.contracts:10d} "
            f"{_fmt_money(level.unsigned_gex_per_1pct):>22} "
            f"{_fmt_money(level.heuristic_signed_gex_per_1pct):>28}"
        )

    print(f"\nSAVED CONTRACTS: {output_contracts}")
    print(f"SAVED LEVELS: {output_levels}")
    print(
        "NOTE: Gamma is Black-76 gamma with respect to the parity-implied forward. "
        "GEX/GAX outputs are therefore forward-based hedge-curvature proxies. Signed "
        "exposure remains the call-positive / put-negative structural heuristic."
    )


if __name__ == "__main__":
    main()
