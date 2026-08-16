from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_hedge_robustness import (
    DEFAULT_COVERAGE_FLOORS,
    lowest_coverage_rows,
    score_core_pair_sensitivity,
    score_hedge_lead_lag,
)


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_HORIZONS = (1, 5, 15, 30, 60)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--date must use YYYY-MM-DD") from exc


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        result = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--horizons must be comma-separated integers") from exc
    if not result or any(item < 1 for item in result):
        raise argparse.ArgumentTypeError("--horizons must contain positive minutes")
    return result


def _raw_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_minute_features.csv"


def _hedge_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_hedge_features.csv"


def _sensitivity_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_hedge_coverage_sensitivity.csv"


def _lead_lag_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_hedge_lead_lag.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run zero-cost GEXY hedge-flow robustness checks: fixed-pair raw-vs-hedge comparisons across "
            "Greek-volume coverage floors plus contemporaneous-vs-forward lead/lag diagnostics."
        )
    )
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument(
        "--horizons",
        type=_parse_horizons,
        default=DEFAULT_HORIZONS,
        help="forward-return horizons in minutes; default: 1,5,15,30,60",
    )
    parser.add_argument(
        "--lead-lag-min-volume-coverage",
        type=float,
        default=0.90,
        help="minimum classified contract-volume Greek coverage for lead/lag scoring; default: 0.90",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing local raw-flow and hedge-flow feature CSVs",
    )
    args = parser.parse_args()

    raw_path = _raw_path(args.data_dir, args.trading_day)
    hedge_path = _hedge_path(args.data_dir, args.trading_day)
    if not raw_path.exists():
        raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
    if not hedge_path.exists():
        raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")

    raw = pd.read_csv(raw_path)
    hedge = pd.read_csv(hedge_path)
    try:
        lowest = lowest_coverage_rows(raw, hedge)
        sensitivity = score_core_pair_sensitivity(
            raw,
            hedge,
            horizons_minutes=args.horizons,
            coverage_floors=DEFAULT_COVERAGE_FLOORS,
        )
        lead_lag = score_hedge_lead_lag(
            raw,
            hedge,
            min_volume_coverage=float(args.lead_lag_min_volume_coverage),
            horizons_minutes=args.horizons,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    sensitivity_path = _sensitivity_path(args.data_dir, args.trading_day)
    lead_lag_path = _lead_lag_path(args.data_dir, args.trading_day)
    sensitivity.to_csv(sensitivity_path, index=False)
    lead_lag.to_csv(lead_lag_path, index=False)

    print("GEXY HEDGE-FLOW ROBUSTNESS / LEAD-LAG")
    print(f"DATE: {args.trading_day.isoformat()}")
    print("FIXED CORE PAIRS: net contracts->delta, call contracts->call delta, put contracts->put delta")
    print("COVERAGE FLOORS: " + ",".join(f"{item:.0%}" for item in DEFAULT_COVERAGE_FLOORS))
    print(f"LEAD/LAG MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.lead_lag_min_volume_coverage:.0%}")
    print("INTERPRETATION: descriptive one-day pilot only; no fitted model or out-of-sample claim")

    if not lowest.empty:
        print("\nLOWEST REPLAY-MATCHED GREEK-VOLUME COVERAGE ROWS")
        print(lowest.to_string(index=False))

    if not sensitivity.empty:
        print("\nFIXED-PAIR ABS-SPEARMAN AT 90%+ VOLUME COVERAGE")
        view = sensitivity.loc[sensitivity["min_volume_coverage"] == 0.90].copy()
        display = [
            "horizon_minutes",
            "pair",
            "family",
            "signal",
            "observations",
            "spearman",
            "abs_spearman",
            "top_minus_bottom_target_bps",
        ]
        print(view[display].to_string(index=False))

    if not lead_lag.empty:
        print("\nHEDGE MECHANISM LEAD/LAG — ABS-SPEARMAN")
        pivot = lead_lag.pivot(index="signal", columns="period", values="abs_spearman")
        preferred = ["contemporaneous_flow_minute", *[f"forward_{item}m" for item in args.horizons]]
        columns = [column for column in preferred if column in pivot.columns]
        print(pivot[columns].to_string())

    print(f"\nSENSITIVITY CSV: {sensitivity_path}")
    print(f"LEAD/LAG CSV: {lead_lag_path}")
    print("NO PAID DATA REQUESTS: this robustness check reads only local causal feature CSVs.")


if __name__ == "__main__":
    main()
