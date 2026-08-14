from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Any

from packages.data.alpaca_options import AlpacaOptionsClient, AlpacaOptionsError
from packages.gexy.levels import rank_levels_by_unsigned_gex
from packages.gexy.normalization import normalize_alpaca_option_surface
from packages.gexy.pipeline import build_enriched_gexy_surface


def _contracts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("option_contracts")
    if raw is None:
        raw = payload.get("contracts")
    return [item for item in raw or [] if isinstance(item, dict)]


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    amount = abs(value)
    if amount >= 1_000_000_000:
        return f"{sign}${amount / 1_000_000_000:.3f}B"
    if amount >= 1_000_000:
        return f"{sign}${amount / 1_000_000:.3f}M"
    if amount >= 1_000:
        return f"{sign}${amount / 1_000:.3f}K"
    return f"{sign}${amount:.2f}"


def _wall_strike(level: Any) -> str:
    return "n/a" if level is None else f"{level.strike:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a real GEXY SPX option surface from Alpaca contract OI + snapshots, "
            "including local Greek fallback when the feed omits Greeks."
        )
    )
    parser.add_argument("--symbol", default="SPX", help="Underlying symbol (default: SPX).")
    parser.add_argument("--expiration", required=True, help="Target expiration date, YYYY-MM-DD.")
    parser.add_argument("--spot", required=True, type=float, help="Current underlying spot/index level.")
    parser.add_argument(
        "--time-to-expiry-hours",
        required=True,
        type=float,
        help=(
            "Remaining time to this option series' settlement/expiry in hours. "
            "Required so GEXY does not assume one settlement time for every SPX series."
        ),
    )
    parser.add_argument(
        "--strike-width",
        type=float,
        default=250.0,
        help="Include strikes within +/- this many SPX points of spot (default: 250).",
    )
    parser.add_argument(
        "--feed",
        choices=("indicative", "opra"),
        default=None,
        help="Alpaca option feed. Defaults to APCA_OPTIONS_FEED / indicative.",
    )
    parser.add_argument(
        "--root-symbol",
        default=None,
        help="Optional root filter such as SPXW.",
    )
    parser.add_argument(
        "--risk-free-rate",
        type=float,
        default=0.0,
        help="Annualized decimal risk-free rate for local Greek fallback (default: 0).",
    )
    parser.add_argument(
        "--dividend-yield",
        type=float,
        default=0.0,
        help="Annualized decimal dividend yield for local Greek fallback (default: 0).",
    )
    parser.add_argument("--top", type=int, default=10, help="Number of ranked strikes to print.")
    args = parser.parse_args()

    if args.spot <= 0:
        parser.error("--spot must be positive")
    if args.time_to_expiry_hours <= 0:
        parser.error("--time-to-expiry-hours must be positive")
    if args.strike_width <= 0:
        parser.error("--strike-width must be positive")
    if args.top < 1:
        parser.error("--top must be at least 1")

    try:
        expiration = date.fromisoformat(args.expiration)
    except ValueError:
        parser.error("--expiration must be YYYY-MM-DD")

    strike_min = max(0.01, args.spot - args.strike_width)
    strike_max = args.spot + args.strike_width

    try:
        with AlpacaOptionsClient() as client:
            client.check_authentication()
            contracts_payload = client.fetch_option_contracts(
                args.symbol,
                expiration_date=expiration.isoformat(),
                strike_price_gte=strike_min,
                strike_price_lte=strike_max,
                root_symbol=args.root_symbol,
                limit=10_000,
            )
            contracts = _contracts(contracts_payload)
            symbols = [str(item.get("symbol") or "").strip() for item in contracts]
            symbols = [symbol for symbol in symbols if symbol]
            if not symbols:
                print("GEXY surface sample: no option contracts matched the requested range.", file=sys.stderr)
                return 2

            snapshots_payload = client.fetch_option_snapshots_batched(
                symbols,
                feed=args.feed,
            )
    except (AlpacaOptionsError, ValueError) as exc:
        print(f"GEXY surface sample failed: {exc}", file=sys.stderr)
        return 1

    normalized = normalize_alpaca_option_surface(contracts_payload, snapshots_payload)
    result = build_enriched_gexy_surface(
        normalized,
        spot=args.spot,
        time_to_expiry_years={
            expiration: args.time_to_expiry_hours / (24.0 * 365.0)
        },
        risk_free_rate=args.risk_free_rate,
        dividend_yield=args.dividend_yield,
    )
    ranking = rank_levels_by_unsigned_gex(result.surface, limit=args.top)

    print("GEXY real surface sample")
    print(f"Underlying: {args.symbol.strip().upper()}  Spot: {args.spot:.2f}")
    print(f"Expiration: {expiration.isoformat()}  TTE hours: {args.time_to_expiry_hours:.3f}")
    print(f"Contracts normalized: {len(normalized.points)} / {normalized.contracts_seen}")
    print(f"Missing snapshots: {normalized.missing_snapshots}")
    print(
        "Greek sources: "
        f"alpaca={result.greek_sources.alpaca}, "
        f"alpaca_iv={result.greek_sources.alpaca_iv}, "
        f"quote_iv={result.greek_sources.quote_implied_iv}, "
        f"unavailable={result.greek_sources.unavailable}"
    )
    print(
        f"Exposure contracts used: {result.surface.contracts_used}; "
        f"missing gamma: {result.surface.contracts_missing_gamma}"
    )
    print(f"Total GAX / SPX point: {_money(result.surface.total_gax_notional_per_point)}")
    print(f"Total unsigned GEX / 1%: {_money(result.surface.total_unsigned_gex_per_1pct)}")
    print(
        "Heuristic signed GEX / 1%: "
        f"{_money(result.surface.total_heuristic_signed_gex_per_1pct)}"
    )
    print(
        "Walls: "
        f"unsigned={_wall_strike(result.walls.strongest_unsigned)}, "
        f"positive_heuristic={_wall_strike(result.walls.strongest_positive_heuristic)}, "
        f"negative_heuristic={_wall_strike(result.walls.strongest_negative_heuristic)}, "
        f"below={_wall_strike(result.walls.nearest_below_spot)}, "
        f"above={_wall_strike(result.walls.nearest_above_spot)}"
    )

    print("Top strikes by unsigned GEX:")
    for level in ranking:
        print(
            f"  {level.strike:8.2f}  "
            f"GEX={_money(level.unsigned_gex_per_1pct):>12}  "
            f"signed={_money(level.heuristic_signed_gex_per_1pct):>12}  "
            f"GAX/pt={_money(level.gax_notional_per_point):>12}  "
            f"contracts={level.contracts}"
        )

    if contracts_payload.get("next_page_token"):
        print(
            "Warning: Alpaca reported more contract metadata pages; narrow the strike range "
            "or add contract pagination before treating this as a complete surface.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
