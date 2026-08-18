from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.baseline import (
    DEFAULT_FEATURES,
    evaluate_predictions,
    fit_ridge,
    prepare_baseline_frame,
    purged_chronological_split,
)


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(item < 1 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive minutes")
    return horizons


def _fmt_optional(value: float | None, *, percent: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def _ensure_backward_return(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "backward_return_1m_bps" in result.columns:
        return result
    if "timestamp" not in result.columns or "forward" not in result.columns:
        return result

    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result = result.sort_values("timestamp").reset_index(drop=True)
    current = pd.to_numeric(result["forward"], errors="coerce")
    previous = current.shift(1)
    result["backward_return_1m_bps"] = (current / previous - 1.0) * 10_000.0
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a leakage-safe chronological ridge baseline on GEXY replay features. "
            "This is a research smoke test, not a trading-performance claim."
        )
    )
    parser.add_argument("--features-csv", required=True, type=Path)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 5, 15, 30, 60))
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--alpha", type=float, default=10.0)
    parser.add_argument("--top-features", type=int, default=8)
    args = parser.parse_args()

    if args.top_features < 1:
        raise SystemExit("--top-features must be at least 1")

    raw = pd.read_csv(args.features_csv)
    raw = _ensure_backward_return(raw)

    summary_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []

    print(f"INPUT FEATURE ROWS: {len(raw)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"TRAIN FRACTION BEFORE PURGE: {args.train_fraction:.0%}")
    print(f"RIDGE ALPHA: {args.alpha:g}")
    print("VALIDATION: chronological holdout with horizon purge; train-only imputation/scaling")

    for horizon in args.horizons:
        prepared, features, target = prepare_baseline_frame(
            raw,
            horizon_minutes=horizon,
            feature_candidates=DEFAULT_FEATURES,
        )
        split = purged_chronological_split(
            prepared,
            horizon_minutes=horizon,
            train_fraction=args.train_fraction,
        )
        model = fit_ridge(
            split.train,
            features=features,
            target=target,
            alpha=args.alpha,
        )

        actual = pd.to_numeric(split.test[target], errors="coerce")
        ridge_prediction = model.predict(split.test)
        zero_prediction = np.zeros(len(split.test), dtype=float)
        momentum_prediction = pd.to_numeric(
            split.test["backward_return_1m_bps"], errors="coerce"
        ).fillna(0.0).to_numpy(dtype=float)

        ridge_metrics = evaluate_predictions(actual, ridge_prediction)
        zero_metrics = evaluate_predictions(actual, zero_prediction)
        momentum_metrics = evaluate_predictions(actual, momentum_prediction)

        summary_rows.append(
            {
                "horizon_minutes": horizon,
                "labeled_rows": len(prepared),
                "train_rows_after_purge": len(split.train),
                "test_rows": len(split.test),
                "test_start": split.test_start,
                "features_used": len(model.features),
                "ridge_mae_bps": ridge_metrics.mae_bps,
                "ridge_rmse_bps": ridge_metrics.rmse_bps,
                "ridge_correlation": ridge_metrics.correlation,
                "ridge_directional_accuracy": ridge_metrics.directional_accuracy,
                "zero_mae_bps": zero_metrics.mae_bps,
                "zero_rmse_bps": zero_metrics.rmse_bps,
                "momentum_mae_bps": momentum_metrics.mae_bps,
                "momentum_rmse_bps": momentum_metrics.rmse_bps,
                "momentum_correlation": momentum_metrics.correlation,
                "momentum_directional_accuracy": momentum_metrics.directional_accuracy,
            }
        )

        predictions = pd.DataFrame(
            {
                "timestamp": split.test["timestamp"].to_numpy(),
                "horizon_minutes": horizon,
                "actual_forward_return_bps": actual.to_numpy(dtype=float),
                "ridge_prediction_bps": ridge_prediction,
                "zero_prediction_bps": zero_prediction,
                "momentum_prediction_bps": momentum_prediction,
            }
        )
        prediction_rows.append(predictions)

        coefficients = model.standardized_coefficients().sort_values(
            key=lambda series: series.abs(), ascending=False
        )

        print(f"\nHORIZON {horizon}m")
        print(f"LABELED / TRAIN / TEST: {len(prepared)} / {len(split.train)} / {len(split.test)}")
        print(f"TEST START UTC: {split.test_start}")
        print(f"FEATURES USED: {len(model.features)}")
        print(
            "RIDGE: "
            f"MAE={ridge_metrics.mae_bps:.3f}bps "
            f"RMSE={ridge_metrics.rmse_bps:.3f}bps "
            f"CORR={_fmt_optional(ridge_metrics.correlation)} "
            f"DIR={_fmt_optional(ridge_metrics.directional_accuracy, percent=True)}"
        )
        print(
            "NO-MOVE: "
            f"MAE={zero_metrics.mae_bps:.3f}bps "
            f"RMSE={zero_metrics.rmse_bps:.3f}bps"
        )
        print(
            "1M-MOMENTUM: "
            f"MAE={momentum_metrics.mae_bps:.3f}bps "
            f"RMSE={momentum_metrics.rmse_bps:.3f}bps "
            f"CORR={_fmt_optional(momentum_metrics.correlation)} "
            f"DIR={_fmt_optional(momentum_metrics.directional_accuracy, percent=True)}"
        )
        print("TOP STANDARDIZED RIDGE COEFFICIENTS")
        for feature, coefficient in coefficients.head(args.top_features).items():
            print(f"  {feature}: {coefficient:+.4f} bps per train-SD")

    summary = pd.DataFrame(summary_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    stem = args.features_csv.stem
    summary_path = args.features_csv.with_name(f"{stem}_baseline_summary.csv")
    predictions_path = args.features_csv.with_name(f"{stem}_baseline_predictions.csv")
    summary.to_csv(summary_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    print("\nSUMMARY")
    display_columns = [
        "horizon_minutes",
        "train_rows_after_purge",
        "test_rows",
        "ridge_mae_bps",
        "ridge_rmse_bps",
        "ridge_correlation",
        "ridge_directional_accuracy",
        "zero_mae_bps",
        "momentum_mae_bps",
        "momentum_directional_accuracy",
    ]
    print(summary[display_columns].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED PREDICTIONS: {predictions_path}")
    print(
        "NOTE: A single 0DTE session is enough to validate the research pipeline, but not to "
        "establish statistical predictiveness. Multi-day walk-forward testing is required before "
        "interpreting any apparent advantage as an edge."
    )


if __name__ == "__main__":
    main()
