from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.baseline import (
    STATIONARY_FEATURES,
    evaluate_predictions,
    fit_stationary_ridge,
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
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result = result.sort_values("timestamp").reset_index(drop=True)
    current = pd.to_numeric(result["forward"], errors="coerce")
    previous = current.shift(1)
    result["backward_return_1m_bps"] = (current / previous - 1.0) * 10_000.0
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run GEXY's robust stationary-feature ridge baseline. The model excludes "
            "absolute time-to-expiry and absolute GEX/GAX levels, uses train-only robust "
            "scaling, zero return intercept, a purged chronological holdout, and bounded "
            "prediction extrapolation."
        )
    )
    parser.add_argument("--features-csv", required=True, type=Path)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 5, 15, 30, 60))
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--alpha", type=float, default=25.0)
    parser.add_argument("--prediction-quantile", type=float, default=0.99)
    parser.add_argument("--top-features", type=int, default=8)
    args = parser.parse_args()

    raw = pd.read_csv(args.features_csv)
    raw = _ensure_backward_return(raw)

    summary_rows: list[dict[str, object]] = []
    prediction_rows: list[pd.DataFrame] = []

    print(f"INPUT FEATURE ROWS: {len(raw)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"TRAIN FRACTION BEFORE PURGE: {args.train_fraction:.0%}")
    print(f"STATIONARY RIDGE ALPHA: {args.alpha:g}")
    print(f"PREDICTION ABS-BOUND QUANTILE: {args.prediction_quantile:.3f}")
    print(
        "VALIDATION: stationary/change features + chronological holdout + horizon purge + "
        "train-only robust scaling + zero return intercept"
    )

    for horizon in args.horizons:
        prepared, features, target = prepare_baseline_frame(
            raw,
            horizon_minutes=horizon,
            feature_candidates=STATIONARY_FEATURES,
        )
        split = purged_chronological_split(
            prepared,
            horizon_minutes=horizon,
            train_fraction=args.train_fraction,
        )
        model = fit_stationary_ridge(
            split.train,
            features=features,
            target=target,
            alpha=args.alpha,
            prediction_quantile=args.prediction_quantile,
        )

        actual = pd.to_numeric(split.test[target], errors="coerce")
        stationary_prediction = model.predict(split.test)
        zero_prediction = np.zeros(len(split.test), dtype=float)
        momentum_prediction = pd.to_numeric(
            split.test["backward_return_1m_bps"], errors="coerce"
        ).fillna(0.0).to_numpy(dtype=float)

        stationary_metrics = evaluate_predictions(actual, stationary_prediction)
        zero_metrics = evaluate_predictions(actual, zero_prediction)
        momentum_metrics = evaluate_predictions(actual, momentum_prediction)
        mae_vs_zero_pct = (
            (stationary_metrics.mae_bps / zero_metrics.mae_bps - 1.0) * 100.0
            if zero_metrics.mae_bps > 0
            else float("nan")
        )

        summary_rows.append(
            {
                "horizon_minutes": horizon,
                "labeled_rows": len(prepared),
                "train_rows_after_purge": len(split.train),
                "test_rows": len(split.test),
                "test_start": split.test_start,
                "features_used": len(model.features),
                "stationary_mae_bps": stationary_metrics.mae_bps,
                "stationary_rmse_bps": stationary_metrics.rmse_bps,
                "stationary_correlation": stationary_metrics.correlation,
                "stationary_directional_accuracy": stationary_metrics.directional_accuracy,
                "stationary_mae_vs_zero_pct": mae_vs_zero_pct,
                "zero_mae_bps": zero_metrics.mae_bps,
                "zero_rmse_bps": zero_metrics.rmse_bps,
                "momentum_mae_bps": momentum_metrics.mae_bps,
                "momentum_rmse_bps": momentum_metrics.rmse_bps,
                "momentum_correlation": momentum_metrics.correlation,
                "momentum_directional_accuracy": momentum_metrics.directional_accuracy,
                "prediction_floor_bps": model.prediction_floor,
                "prediction_ceiling_bps": model.prediction_ceiling,
            }
        )

        prediction_rows.append(
            pd.DataFrame(
                {
                    "timestamp": split.test["timestamp"].to_numpy(),
                    "horizon_minutes": horizon,
                    "actual_forward_return_bps": actual.to_numpy(dtype=float),
                    "stationary_prediction_bps": stationary_prediction,
                    "zero_prediction_bps": zero_prediction,
                    "momentum_prediction_bps": momentum_prediction,
                }
            )
        )

        coefficients = model.standardized_coefficients().sort_values(
            key=lambda series: series.abs(), ascending=False
        )

        print(f"\nHORIZON {horizon}m")
        print(f"LABELED / TRAIN / TEST: {len(prepared)} / {len(split.train)} / {len(split.test)}")
        print(f"TEST START UTC: {split.test_start}")
        print(f"FEATURES USED: {len(model.features)}")
        print(
            "STATIONARY RIDGE: "
            f"MAE={stationary_metrics.mae_bps:.3f}bps "
            f"RMSE={stationary_metrics.rmse_bps:.3f}bps "
            f"CORR={_fmt_optional(stationary_metrics.correlation)} "
            f"DIR={_fmt_optional(stationary_metrics.directional_accuracy, percent=True)} "
            f"MAE-vs-ZERO={mae_vs_zero_pct:+.1f}%"
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
        print(
            "TRAIN-DERIVED PREDICTION BOUNDS: "
            f"{model.prediction_floor:.3f} to {model.prediction_ceiling:.3f} bps"
        )
        print("TOP STANDARDIZED STATIONARY COEFFICIENTS")
        for feature, coefficient in coefficients.head(args.top_features).items():
            print(f"  {feature}: {coefficient:+.4f} bps per robust train scale")

    summary = pd.DataFrame(summary_rows)
    predictions = pd.concat(prediction_rows, ignore_index=True)
    stem = args.features_csv.stem
    summary_path = args.features_csv.with_name(f"{stem}_stationary_summary.csv")
    predictions_path = args.features_csv.with_name(f"{stem}_stationary_predictions.csv")
    summary.to_csv(summary_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    print("\nSUMMARY")
    display_columns = [
        "horizon_minutes",
        "train_rows_after_purge",
        "test_rows",
        "stationary_mae_bps",
        "stationary_rmse_bps",
        "stationary_correlation",
        "stationary_directional_accuracy",
        "stationary_mae_vs_zero_pct",
        "zero_mae_bps",
        "momentum_mae_bps",
        "momentum_directional_accuracy",
    ]
    print(summary[display_columns].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED PREDICTIONS: {predictions_path}")
    print(
        "NOTE: This v2 baseline is designed to diagnose whether hedge-surface changes carry "
        "signal without relying on monotonic intraday state. One session remains a pipeline "
        "diagnostic only; multi-day walk-forward validation is required for an edge claim."
    )


if __name__ == "__main__":
    main()
