from __future__ import annotations

import argparse
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from packages.gexy.exposure import build_gex_surface
from packages.gexy.greeks import black_scholes_greeks, implied_volatility_from_price
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
    if normalized == "call":
        return OptionType.CALL
    if normalized == "put":
        return OptionType.PUT
    raise ValueError(f"unsupported option_type: {value}")


def _recover_shared_otm_iv(
    frame: pd.DataFrame,
    *,
    forward_proxy: float,
    time_to_expiry_years: float,
) -> tuple[pd.DataFrame, int, int]:
    result = frame.copy()
    recovered = 0
    pair_iv_strikes = 0

    for strike, group in result.groupby("strike", sort=True):
        calls = group[group["option_type"].astype(str).str.lower() == "call"]
        puts = group[group["option_type"].astype(str).str.lower() == "put"]
        if calls.empty or puts.empty:
            continue

        call = calls.iloc[-1]
        put = puts.iloc[-1]
        use_call = float(strike) >= forward_proxy
        source = call if use_call else put
        source_type = OptionType.CALL if use_call else OptionType.PUT
        option_price = source.get("mid")
        if pd.isna(option_price):
            continue

        volatility = implied_volatility_from_price(
            option_type=source_type,
            option_price=float(option_price),
            spot=forward_proxy,
            strike=float(strike),
            time_to_expiry_years=time_to_expiry_years,
            risk_free_rate=0.0,
            dividend_yield=0.0,
        )
        if volatility is None:
            continue

        pair_iv_strikes += 1
        missing_indexes = group.index[group["gamma"].isna()]
        for index in missing_indexes:
            row = result.loc[index]
            greeks = black_scholes_greeks(
                option_type=_option_type(str(row["option_type"])),
                spot=forward_proxy,
                strike=float(strike),
                time_to_expiry_years=time_to_expiry_years,
                volatility=volatility,
                risk_free_rate=0.0,
                dividend_yield=0.0,
            )
            result.at[index, "implied_volatility"] = volatility
            result.at[index, "gamma"] = greeks.gamma
            result.at[index, "greek_source"] = "paired_otm_iv"
            recovered += 1

    return result, recovered, pair_iv_strikes


def _points_from_frame(
    frame: pd.DataFrame,
    *,
    expiration: date,
    open_interest_date: date,
) -> list[OptionSurfacePoint]:
    points: list[OptionSurfacePoint] = []
    for row in frame.itertuples(index=False):
        gamma = float(row.gamma) if pd.notna(row.gamma) else None
        points.append(
            OptionSurfacePoint(
                symbol=str(row.symbol),
                underlying_symbol="SPX",
                expiration_date=expiration,
                option_type=_option_type(str(row.option_type)),
                strike=float(row.strike),
                multiplier=SPX_MULTIPLIER,
                open_interest=float(row.open_interest),
                open_interest_date=open_interest_date,
                bid=float(row.bid) if pd.notna(row.bid) else None,
                ask=float(row.ask) if pd.notna(row.ask) else None,
                implied_volatility=(
                    float(row.implied_volatility)
                    if pd.notna(row.implied_volatility)
                    else None
                ),
                gamma=gamma,
            )
        )
    return points


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Recover missing 0DTE SPXW Greeks by solving IV from the paired OTM leg. "
            "This is an offline post-process and makes no Databento requests."
        )
    )
    parser.add_argument("--contracts-csv", required=True, type=Path)
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument("--expiration", required=True, type=_parse_date)
    parser.add_argument("--quote-time", required=True, type=_parse_clock)
    parser.add_argument("--forward", required=True, type=float)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    if args.forward <= 0:
        raise SystemExit("--forward must be positive")
    if args.top < 1:
        raise SystemExit("--top must be at least 1")

    frame = pd.read_csv(args.contracts_csv)
    required = {
        "symbol",
        "option_type",
        "strike",
        "open_interest",
        "mid",
        "implied_volatility",
        "gamma",
        "greek_source",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise SystemExit(f"contracts CSV missing required columns: {', '.join(missing)}")

    quote_time = datetime.combine(args.trading_day, args.quote_time, tzinfo=NY)
    expiration_time = datetime.combine(args.expiration, time(16, 0), tzinfo=NY)
    if expiration_time <= quote_time:
        raise SystemExit("expiration must be after quote time")

    time_to_expiry_years = (
        expiration_time - quote_time
    ).total_seconds() / (365.0 * 24.0 * 60.0 * 60.0)

    initial_solved = int(frame["gamma"].notna().sum())
    recovered_frame, recovered, pair_iv_strikes = _recover_shared_otm_iv(
        frame,
        forward_proxy=args.forward,
        time_to_expiry_years=time_to_expiry_years,
    )

    points = _points_from_frame(
        recovered_frame,
        expiration=args.expiration,
        open_interest_date=args.trading_day,
    )
    surface = build_gex_surface(points, args.forward)
    walls = summarize_gex_walls(surface)
    ranked = rank_levels_by_unsigned_gex(surface, limit=args.top)

    output_contracts = args.contracts_csv.with_name(
        f"{args.contracts_csv.stem}_paired_recovered.csv"
    )
    output_levels = args.contracts_csv.with_name(
        f"{args.contracts_csv.stem}_paired_levels.csv"
    )
    recovered_frame.to_csv(output_contracts, index=False)
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
    ).to_csv(output_levels, index=False)

    print(f"INPUT CONTRACTS: {len(frame)}")
    print(f"INITIAL GREEKS SOLVED: {initial_solved}")
    print(f"PAIRED OTM IV STRIKES: {pair_iv_strikes}")
    print(f"GREEKS RECOVERED FROM PAIRED OTM IV: {recovered}")
    print(f"GREEKS SOLVED AFTER RECOVERY: {surface.contracts_used}")
    print(f"GREEKS UNAVAILABLE AFTER RECOVERY: {surface.contracts_missing_gamma}")
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

    print(f"\nSAVED CONTRACTS: {output_contracts}")
    print(f"SAVED LEVELS: {output_levels}")
    print(
        "NOTE: Missing Greeks are filled only when a same-strike call/put pair exists "
        "and the OTM leg yields a valid implied volatility. Existing solved Greeks are "
        "left unchanged. Signed GEX remains a call-positive / put-negative heuristic."
    )


if __name__ == "__main__":
    main()
