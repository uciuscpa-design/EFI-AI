from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.off_exchange import (
    OFF_EXCHANGE_FEATURES,
    add_causal_large_print_flags,
    aggregate_completed_minute_off_exchange,
    normalize_off_exchange_trades,
)


def _parse_values(value: str) -> tuple[str, ...]:
    result = tuple(item.strip() for item in value.split(",") if item.strip())
    if not result:
        raise argparse.ArgumentTypeError("value list must contain at least one item")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build strictly causal GEXY off-exchange/TRF completed-minute features from a local trade CSV. "
            "This command makes no market-data requests and does not infer buyer/seller identity or intent."
        )
    )
    parser.add_argument("--input", required=True, type=Path, help="local trade CSV")
    parser.add_argument("--output", required=True, type=Path, help="output minute-feature CSV")
    parser.add_argument("--available-at-col", default="ts_recv")
    parser.add_argument("--symbol-col", default="symbol")
    parser.add_argument("--price-col", default="price")
    parser.add_argument("--size-col", default="size")
    parser.add_argument("--venue-col", default="publisher_id")
    parser.add_argument(
        "--off-exchange-col",
        default=None,
        help="optional source-provided boolean-like off-exchange marker; disables venue allow-list requirement",
    )
    parser.add_argument(
        "--off-exchange-venues",
        type=_parse_values,
        default=None,
        help=(
            "explicit comma-separated off-exchange/TRF venue or publisher values. Required unless "
            "--off-exchange-col is supplied. Do not guess or use generic trade-condition codes."
        ),
    )
    parser.add_argument("--source", default="local_csv")
    parser.add_argument("--large-lookback-prints", type=int, default=200)
    parser.add_argument("--large-min-periods", type=int, default=30)
    parser.add_argument("--large-quantile", type=float, default=0.95)
    parser.add_argument("--anomaly-lookback-minutes", type=int, default=120)
    parser.add_argument("--anomaly-min-periods", type=int, default=30)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"input CSV was not found: {args.input}")
    if args.off_exchange_col is None and args.off_exchange_venues is None:
        raise SystemExit("provide --off-exchange-col or an explicit --off-exchange-venues allow-list")

    raw = pd.read_csv(args.input)
    try:
        normalized = normalize_off_exchange_trades(
            raw,
            available_at_col=args.available_at_col,
            symbol_col=args.symbol_col,
            price_col=args.price_col,
            size_col=args.size_col,
            venue_col=args.venue_col if args.venue_col else None,
            off_exchange_col=args.off_exchange_col,
            off_exchange_venues=args.off_exchange_venues,
            source=args.source,
        )
        if normalized.empty:
            raise ValueError("no usable off-exchange prints remained after explicit source filtering")
        flagged = add_causal_large_print_flags(
            normalized,
            lookback_prints=args.large_lookback_prints,
            min_periods=args.large_min_periods,
            quantile=args.large_quantile,
        )
        features = aggregate_completed_minute_off_exchange(
            flagged,
            anomaly_lookback_minutes=args.anomaly_lookback_minutes,
            anomaly_min_periods=args.anomaly_min_periods,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(args.output, index=False)

    print("GEXY OFF-EXCHANGE / TRF CAUSAL FEATURES")
    print(f"INPUT CSV: {args.input}")
    print(f"NORMALIZED OFF-EXCHANGE PRINTS: {len(normalized)}")
    print(f"COMPLETED MINUTES: {len(features)}")
    print(f"FEATURES: {len(OFF_EXCHANGE_FEATURES)}")
    print("CAUSAL ALIGNMENT: prints observable during minute M are timestamped M+1")
    print("IDENTITY POLICY: no buyer/seller, dark-pool identity, or informed-trader intent is inferred")
    print(f"OUTPUT CSV: {args.output}")
    print("\nLAST 8 COMPLETED MINUTES")
    display = [
        "offx_minute",
        "timestamp",
        "offx_trade_records",
        "offx_unique_symbols",
        "offx_share_volume",
        "offx_notional",
        "offx_large_print_records",
        "offx_large_print_volume_share",
        "offx_repeated_level_groups",
        "off_exchange_anomaly_score",
    ]
    print(features[display].tail(8).to_string(index=False))
    print("\nNO PAID DATA REQUESTS: this builder reads only the local input CSV.")


if __name__ == "__main__":
    main()
