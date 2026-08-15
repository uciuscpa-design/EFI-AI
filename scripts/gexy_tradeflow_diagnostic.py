from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_diagnostics import DEFAULT_SIGNAL_COLUMNS, score_flow_signals


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


def _input_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_minute_features.csv"


def _output_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tradeflow_diagnostic.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run descriptive GEXY trade-flow versus future-move diagnostics on the local causal minute dataset. "
            "No model is fit and no market-data request is made."
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
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing the local causal trade-flow feature CSV",
    )
    args = parser.parse_args()

    source = _input_path(args.data_dir, args.trading_day)
    if not source.exists():
        raise SystemExit(f"causal trade-flow feature CSV was not found: {source}")

    frame = pd.read_csv(source)
    results = score_flow_signals(frame, horizons_minutes=args.horizons)
    if results.empty:
        raise SystemExit("no finite diagnostic rows were available")

    output = _output_path(args.data_dir, args.trading_day)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)

    print("GEXY EXPLORATORY TRADE-FLOW DIAGNOSTIC")
    print(f"DATE: {args.trading_day.isoformat()}")
    print(f"SIGNALS SCORED: {len(DEFAULT_SIGNAL_COLUMNS)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print("INTERPRETATION: descriptive one-day pilot only; no fitted model and no out-of-sample claim")
    print(f"OUTPUT CSV: {output}")

    display = [
        "horizon_minutes",
        "signal",
        "observations",
        "spearman",
        "pearson",
        "directional_accuracy_same_sign",
        "bottom_quartile_mean_forward_bps",
        "top_quartile_mean_forward_bps",
        "top_minus_bottom_forward_bps",
    ]
    print("\nTOP 3 ABS-SPEARMAN SIGNALS PER HORIZON")
    top = results.groupby("horizon_minutes", sort=True, group_keys=False).head(3)
    print(top[display].to_string(index=False))
    print("\nNO PAID DATA REQUESTS: this diagnostic reads only the local causal minute feature CSV.")


if __name__ == "__main__":
    main()
