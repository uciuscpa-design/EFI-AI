from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_window_regime import (
    evaluate_window_day,
    pooled_window_endpoints,
    summarize_window_days,
)


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_MIN_VOLUME_COVERAGE = 0.90
FROZEN_HORIZONS = (5, 15)
PRIMARY_HORIZON = 15
SECONDARY_HORIZON = 5


def _parse_dates(value: str) -> tuple[str, ...]:
    dates = tuple(item.strip() for item in value.split(",") if item.strip())
    if not dates:
        raise argparse.ArgumentTypeError("--dates must contain at least one YYYY-MM-DD date")
    for item in dates:
        try:
            parsed = pd.Timestamp(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates") from exc
        if parsed.strftime("%Y-%m-%d") != item:
            raise argparse.ArgumentTypeError("--dates must be comma-separated YYYY-MM-DD dates")
    return dates


def _raw_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: str) -> Path:
    return data_dir / f"gexy_spxw_{day}_tradeflow_hedge_features.csv"


def _load_daily_frames(
    data_dir: Path,
    dates: tuple[str, ...],
) -> list[tuple[str, pd.DataFrame, pd.DataFrame]]:
    daily: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    for day in dates:
        raw_path = _raw_path(data_dir, day)
        hedge_path = _hedge_path(data_dir, day)
        if not raw_path.exists():
            raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
        if not hedge_path.exists():
            raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")
        daily.append((day, pd.read_csv(raw_path), pd.read_csv(hedge_path)))
    return daily


def _opening_rows(
    daily: list[tuple[str, pd.DataFrame, pd.DataFrame]],
    *,
    min_volume_coverage: float,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for day, raw, hedge in daily:
        scored = evaluate_window_day(
            raw,
            hedge,
            trading_day=day,
            min_volume_coverage=min_volume_coverage,
            horizons_minutes=FROZEN_HORIZONS,
        )
        scored = scored.loc[scored["session_window"] == "opening"].copy()
        frames.append(scored)
    result = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    if result.empty:
        raise SystemExit("no opening-window validation rows were available")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen GEXY batch-3 opening-window validation endpoints from local feature CSVs. "
            "Primary is opening 15m net delta; secondary is opening 5m. Makes no market-data request."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument(
        "--min-volume-coverage",
        type=float,
        default=DEFAULT_MIN_VOLUME_COVERAGE,
        help="minimum classified contract volume with usable Greeks; frozen default: 0.90",
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

    daily = _load_daily_frames(args.data_dir, args.dates)
    per_day = _opening_rows(daily, min_volume_coverage=args.min_volume_coverage)
    summary = summarize_window_days(per_day)
    pooled = pooled_window_endpoints(
        daily,
        min_volume_coverage=args.min_volume_coverage,
        horizons_minutes=FROZEN_HORIZONS,
    )
    pooled = pooled.loc[pooled["session_window"] == "opening"].copy()

    by_day_output = args.data_dir / "gexy_spxw_tradeflow_opening_validation_batch_3_by_day.csv"
    summary_output = args.data_dir / "gexy_spxw_tradeflow_opening_validation_batch_3_summary.csv"
    pooled_output = args.data_dir / "gexy_spxw_tradeflow_opening_validation_batch_3_pooled.csv"
    args.data_dir.mkdir(parents=True, exist_ok=True)
    per_day.to_csv(by_day_output, index=False)
    summary.to_csv(summary_output, index=False)
    pooled.to_csv(pooled_output, index=False)

    display_columns = [
        "trading_day",
        "observations",
        "momentum_spearman",
        "raw_partial_spearman_controlling_momentum",
        "hedge_spearman",
        "hedge_partial_spearman_controlling_momentum_and_raw",
        "negative_sign",
    ]

    primary = per_day.loc[per_day["horizon_minutes"] == PRIMARY_HORIZON, display_columns]
    secondary = per_day.loc[per_day["horizon_minutes"] == SECONDARY_HORIZON, display_columns]
    primary_summary = summary.loc[summary["horizon_minutes"] == PRIMARY_HORIZON]
    secondary_summary = summary.loc[summary["horizon_minutes"] == SECONDARY_HORIZON]

    print("GEXY OPENING-WINDOW VALIDATION BATCH 3 — FROZEN ENDPOINTS")
    print(f"DATES: {','.join(args.dates)}")
    print("WINDOW: 09:30-10:00 America/New_York only")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print("PRIMARY: 15m net_contracts_vs_delta partial Spearman; expected sign negative")
    print("SECONDARY: 5m same endpoint; expected sign negative")
    print("STATUS: untouched validation dates; no signal/horizon/window selection")

    print("\nPRIMARY 15M — DAY BY DAY")
    print(primary.to_string(index=False))
    print("\nPRIMARY 15M — SIGN STABILITY")
    print(primary_summary.to_string(index=False))

    print("\nSECONDARY 5M — DAY BY DAY")
    print(secondary.to_string(index=False))
    print("\nSECONDARY 5M — SIGN STABILITY")
    print(secondary_summary.to_string(index=False))

    print("\nPOOLED OPENING ENDPOINTS WITH CATEGORICAL DAY FIXED EFFECTS — DESCRIPTIVE")
    if pooled.empty:
        print("No pooled opening rows were available.")
    else:
        print(pooled.to_string(index=False))

    print(f"\nBY-DAY CSV: {by_day_output}")
    print(f"SUMMARY CSV: {summary_output}")
    print(f"POOLED CSV: {pooled_output}")
    print("NO PAID DATA REQUESTS: this validator reads only existing local causal feature CSVs.")


if __name__ == "__main__":
    main()
