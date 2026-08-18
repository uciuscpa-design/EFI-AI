from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_opening_control_stability import (
    evaluate_opening_control_day,
    summarize_opening_control_days,
)


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_MIN_VOLUME_COVERAGE = 0.90


def _parse_dates(value: str) -> tuple[str, ...]:
    dates = tuple(item.strip() for item in value.split(",") if item.strip())
    if not dates:
        raise argparse.ArgumentTypeError("--dates must contain at least one YYYY-MM-DD date")
    for item in dates:
        try:
            pd.Timestamp(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates") from exc
    return dates


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the frozen 15-minute GEXY net-delta control structure across existing opening-window sessions. "
            "Post-hoc mechanism diagnostic only; no market-data request."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
        help="minimum classified contract-volume Greek coverage; default: 0.90",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing local raw-flow and hedge-flow feature CSVs",
    )
    args = parser.parse_args()
    if not 0.0 <= args.min_volume_coverage <= 1.0:
        parser.error("--min-volume-coverage must be between 0 and 1")

    rows: list[pd.DataFrame] = []
    for day in args.dates:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        result = evaluate_opening_control_day(
            pd.read_csv(raw_path),
            pd.read_csv(hedge_path),
            trading_day=day,
            min_volume_coverage=args.min_volume_coverage,
        )
        rows.append(result)

    per_day = pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()
    if per_day.empty:
        raise SystemExit("no opening-window 15-minute control-structure rows were available")
    summary = summarize_opening_control_days(per_day)

    by_day_output = args.data_dir / "gexy_spxw_tradeflow_opening_control_stability_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_tradeflow_opening_control_stability_summary.csv"
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)

    display = [
        "trading_day",
        "observations",
        "hedge_target_spearman",
        "hedge_partial_controlling_momentum",
        "hedge_partial_controlling_raw",
        "hedge_partial_controlling_momentum_and_raw",
        "hedge_raw_spearman",
        "hedge_momentum_spearman",
        "raw_momentum_spearman",
        "ordinary_to_both_sign_flip",
    ]
    print("GEXY EIGHT-DAY OPENING 15M CONTROL-STABILITY AUDIT — LOCAL ONLY")
    print(f"DATES: {','.join(args.dates)}")
    print("WINDOW: opening 09:30-10:00 America/New_York")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("HORIZON: 15 minutes only")
    print("SIGNAL: hedge_delta_units")
    print("CONTROLS: backward_return_1m_bps and flow_net_signed_contracts")
    print("STATUS: post-hoc mechanism research; no validation verdict changes")
    print("\nDAY-BY-DAY CONTROL STABILITY")
    print(per_day[display].to_string(index=False))
    print("\nEIGHT-DAY SUMMARY")
    print(summary.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print("NO PAID DATA REQUESTS: this audit reads only existing local causal feature CSVs.")


if __name__ == "__main__":
    main()
