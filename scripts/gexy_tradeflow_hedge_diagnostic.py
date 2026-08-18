from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_hedge_diagnostics import (
    HEDGE_FLOW_SIGNALS,
    RAW_FLOW_SIGNALS,
    align_raw_and_hedge_frames,
    best_family_rows,
    score_raw_vs_hedge,
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


def _output_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_raw_vs_hedge_diagnostic.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare raw GEXY option-flow signals with Black-76 Greek-weighted hedge-flow proxies on identical "
            "causal timestamps and forward-return labels. Descriptive only; no model or market-data request."
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
        aligned = align_raw_and_hedge_frames(raw, hedge)
        results = score_raw_vs_hedge(raw, hedge, horizons_minutes=args.horizons)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if results.empty:
        raise SystemExit("no finite raw-versus-hedge diagnostic rows were available")

    output = _output_path(args.data_dir, args.trading_day)
    output.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output, index=False)

    matched = aligned
    if "replay_match" in matched.columns:
        matched = matched.loc[matched["replay_match"].fillna(False)].copy()
    solved = pd.to_numeric(matched.get("hedge_greek_solved_pct"), errors="coerce")
    volume_solved = pd.to_numeric(
        matched.get("hedge_greek_solved_contract_volume_pct"), errors="coerce"
    )

    print("GEXY RAW FLOW VS GREEK-WEIGHTED HEDGE FLOW")
    print(f"DATE: {args.trading_day.isoformat()}")
    print(f"COMMON CAUSAL TIMESTAMPS: {len(aligned)}")
    print(f"REPLAY-MATCHED COMMON TIMESTAMPS: {len(matched)}")
    if solved.notna().any():
        print(f"MEDIAN HEDGE GREEK SOLVED PCT: {solved.median():.1%}")
        print(f"MIN HEDGE GREEK SOLVED PCT: {solved.min():.1%}")
    if volume_solved.notna().any():
        print(f"MEDIAN CLASSIFIED VOLUME WITH GREEKS: {volume_solved.median():.1%}")
        print(f"MIN CLASSIFIED VOLUME WITH GREEKS: {volume_solved.min():.1%}")
    print(f"RAW SIGNALS: {len(RAW_FLOW_SIGNALS)}")
    print(f"HEDGE SIGNALS: {len(HEDGE_FLOW_SIGNALS)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print("INTERPRETATION: descriptive one-day pilot only; no fitted model and no out-of-sample claim")
    print(f"OUTPUT CSV: {output}")

    best = best_family_rows(results)
    display = [
        "horizon_minutes",
        "family",
        "signal",
        "observations",
        "spearman",
        "pearson",
        "directional_accuracy_same_sign",
        "bottom_quartile_mean_forward_bps",
        "top_quartile_mean_forward_bps",
        "top_minus_bottom_forward_bps",
    ]
    print("\nBEST ABS-SPEARMAN SIGNAL IN EACH FAMILY / HORIZON")
    print(best[display].to_string(index=False))

    print("\nABS-SPEARMAN FAMILY COMPARISON")
    for horizon in args.horizons:
        rows = best.loc[best["horizon_minutes"] == horizon]
        raw_row = rows.loc[rows["family"] == "raw_flow"]
        hedge_row = rows.loc[rows["family"] == "hedge_flow"]
        if raw_row.empty or hedge_row.empty:
            continue
        raw_abs = float(raw_row.iloc[0]["abs_spearman"])
        hedge_abs = float(hedge_row.iloc[0]["abs_spearman"])
        winner = "hedge_flow" if hedge_abs > raw_abs else "raw_flow" if raw_abs > hedge_abs else "tie"
        print(
            f"{horizon:>2}m raw={raw_abs:.3f} hedge={hedge_abs:.3f} "
            f"delta={hedge_abs - raw_abs:+.3f} winner={winner}"
        )

    print("\nNO PAID DATA REQUESTS: this comparison reads only local causal feature CSVs.")


if __name__ == "__main__":
    main()
