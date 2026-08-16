from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_multiday_validation import (
    PRIMARY_HORIZONS,
    evaluate_primary_day,
    pooled_nonoverlap_primary,
    summarize_primary_days,
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
            "Summarize fixed GEXY 5m/15m net-delta primary endpoints across local trade-flow days and run a "
            "deterministic non-overlapping sensitivity check. No model tuning and no market-data request."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
        help="minimum classified contract volume with usable Greeks; default: 0.90",
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

    daily: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    per_day_frames: list[pd.DataFrame] = []
    for day in args.dates:
        raw_path = _raw_path(args.data_dir, day)
        hedge_path = _hedge_path(args.data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        raw = pd.read_csv(raw_path)
        hedge = pd.read_csv(hedge_path)
        daily.append((day, raw, hedge))
        result = evaluate_primary_day(
            raw,
            hedge,
            trading_day=day,
            min_volume_coverage=args.min_volume_coverage,
            horizons_minutes=PRIMARY_HORIZONS,
        )
        per_day_frames.append(result)

    per_day = pd.concat(per_day_frames, ignore_index=True, sort=False) if per_day_frames else pd.DataFrame()
    if per_day.empty:
        raise SystemExit("no multiday primary endpoint rows were available")
    summary = summarize_primary_days(per_day)
    nonoverlap = pooled_nonoverlap_primary(
        daily,
        horizons_minutes=PRIMARY_HORIZONS,
        min_volume_coverage=args.min_volume_coverage,
    )

    by_day_output = args.data_dir / "gexy_spxw_tradeflow_primary_multiday_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_tradeflow_primary_multiday_summary.csv"
    nonoverlap_output = args.data_dir / "gexy_spxw_tradeflow_primary_multiday_nonoverlap.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)
    nonoverlap.to_csv(nonoverlap_output, index=False)

    value_column = "hedge_partial_spearman_controlling_momentum_and_raw"
    display = [
        "trading_day",
        "horizon_minutes",
        "observations",
        "momentum_spearman",
        "raw_partial_spearman_controlling_momentum",
        value_column,
    ]
    print("GEXY MULTIDAY FIXED PRIMARY-ENDPOINT STABILITY")
    print(f"DATES: {','.join(args.dates)}")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("PRIMARY ENDPOINTS: fixed net_contracts_vs_delta at 5m and 15m")
    print("NO SIGNAL SELECTION: day-by-day values use the frozen endpoint definition")
    print("\nDAY-BY-DAY PRIMARY ENDPOINTS")
    print(per_day[display].to_string(index=False))
    print("\nSIGN STABILITY SUMMARY")
    print(summary.to_string(index=False))
    print("\nPOST-HOLDOUT NON-OVERLAPPING SENSITIVITY")
    if nonoverlap.empty:
        print("No finite non-overlapping sensitivity rows were available.")
    else:
        print(nonoverlap.to_string(index=False))
    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"NON-OVERLAP CSV: {nonoverlap_output}")
    print("NO PAID DATA REQUESTS: this analysis reads only local causal feature CSVs.")


if __name__ == "__main__":
    main()
