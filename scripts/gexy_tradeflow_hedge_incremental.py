from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import score_incremental_hedge_information


DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
DEFAULT_HORIZONS = (1, 5, 15, 30, 60)
DEFAULT_MIN_VOLUME_COVERAGE = 0.90


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


def _output_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_hedge_incremental_diagnostic.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Measure whether Greek-weighted GEXY hedge-flow proxies retain forward association after controlling "
            "for the completed flow-minute SPX move and the paired raw-flow signal. Descriptive only; no model "
            "fit for trading and no market-data request."
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

    raw_path = _raw_path(args.data_dir, args.trading_day)
    hedge_path = _hedge_path(args.data_dir, args.trading_day)
    if not raw_path.exists():
        raise SystemExit(f"raw causal trade-flow feature CSV was not found: {raw_path}")
    if not hedge_path.exists():
        raise SystemExit(f"hedge-flow feature CSV was not found: {hedge_path}")

    raw = pd.read_csv(raw_path)
    hedge = pd.read_csv(hedge_path)
    try:
        results = score_incremental_hedge_information(
            raw,
            hedge,
            min_volume_coverage=args.min_volume_coverage,
            horizons_minutes=args.horizons,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if results.empty:
        raise SystemExit("no finite incremental diagnostic rows were available")

    output = _output_path(args.data_dir, args.trading_day)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)

    print("GEXY INCREMENTAL HEDGE-FLOW INFORMATION DIAGNOSTIC")
    print(f"DATE: {args.trading_day.isoformat()}")
    print(f"MIN CLASSIFIED-VOLUME GREEK COVERAGE: {args.min_volume_coverage:.0%}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print("CONTROL 1: completed flow-minute SPX return (backward_return_1m_bps)")
    print("CONTROL 2: paired raw option-flow signal")
    print("INTERPRETATION: rank-partial correlations are descriptive only; one pilot day is not causal proof")
    print(f"OUTPUT CSV: {output}")

    display = [
        "horizon_minutes",
        "pair",
        "observations",
        "momentum_spearman",
        "raw_spearman",
        "raw_partial_spearman_controlling_momentum",
        "hedge_spearman",
        "hedge_partial_spearman_controlling_momentum",
        "hedge_partial_spearman_controlling_momentum_and_raw",
        "mechanical_sign_consistent",
    ]
    print("\nFIXED-PAIR INCREMENTAL RESULTS")
    print(results[display].to_string(index=False))

    print("\nNET-CONTRACTS VS DELTA — HEDGE AFTER BOTH CONTROLS")
    net = results.loc[results["pair"] == "net_contracts_vs_delta", display]
    print(net.to_string(index=False))

    print("\nNO PAID DATA REQUESTS: this diagnostic reads only local causal feature CSVs.")


if __name__ == "__main__":
    main()
