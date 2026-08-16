from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_multiday_validation import PRIMARY_HORIZONS
from packages.gexy.tradeflow_window_regime import (
    evaluate_window_day,
    pooled_window_endpoints,
    summarize_window_days,
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
            "Explore whether the unchanged GEXY net-delta 5m/15m endpoint differs between the already purchased "
            "opening and closing windows. Post-batch exploratory only; no signal selection or market-data request."
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
        per_day_frames.append(
            evaluate_window_day(
                raw,
                hedge,
                trading_day=day,
                min_volume_coverage=args.min_volume_coverage,
                horizons_minutes=PRIMARY_HORIZONS,
            )
        )

    per_day = pd.concat(per_day_frames, ignore_index=True, sort=False) if per_day_frames else pd.DataFrame()
    if per_day.empty:
        raise SystemExit("no window-dependence rows were available")
    summary = summarize_window_days(per_day)
    pooled = pooled_window_endpoints(
        daily,
        min_volume_coverage=args.min_volume_coverage,
        horizons_minutes=PRIMARY_HORIZONS,
    )

    per_day_output = args.data_dir / "gexy_spxw_tradeflow_window_regime_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_tradeflow_window_regime_summary.csv"
    pooled_output = args.data_dir / "gexy_spxw_tradeflow_window_regime_pooled.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    per_day.to_csv(per_day_output, index=False)
    summary.to_csv(summary_output, index=False)
    pooled.to_csv(pooled_output, index=False)

    display = [
        "trading_day",
        "session_window",
        "horizon_minutes",
        "observations",
        "momentum_spearman",
        "raw_partial_spearman_controlling_momentum",
        "hedge_partial_spearman_controlling_momentum_and_raw",
    ]
    print("GEXY POST-BATCH TIME-WINDOW DEPENDENCE — EXPLORATORY")
    print(f"DATES: {','.join(args.dates)}")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("WINDOWS: opening=09:30-10:00, closing=15:30-16:00 America/New_York")
    print("ENDPOINT: unchanged net_contracts_vs_delta at 5m and 15m")
    print("STATUS: post-batch exploratory; any conditional rule would require a later untouched validation set")
    print("\nDAY-BY-DAY WINDOW ENDPOINTS")
    print(per_day[display].to_string(index=False))
    print("\nWINDOW SIGN STABILITY SUMMARY")
    print(summary.to_string(index=False))
    print("\nPOOLED WINDOW ENDPOINTS WITH CATEGORICAL DAY FIXED EFFECTS")
    if pooled.empty:
        print("No pooled window rows were available.")
    else:
        print(pooled.to_string(index=False))
    print(f"\nBY-DAY CSV: {per_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"POOLED CSV: {pooled_output}")
    print("NO PAID DATA REQUESTS: this diagnostic reads only existing local causal feature CSVs.")


if __name__ == "__main__":
    main()
