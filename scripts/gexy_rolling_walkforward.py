from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.baseline import (
    evaluate_predictions,
    fit_stationary_ridge,
    prepare_baseline_frame,
)
from packages.gexy.rolling import (
    DELTA_ONLY_FEATURES,
    choose_shrinkage,
    eligible_history,
    inner_purged_split,
)


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(item < 1 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive minutes")
    return horizons


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


def _directional_accuracy_active(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    mask = np.isfinite(actual) & np.isfinite(predicted) & (predicted != 0) & (actual != 0)
    if not mask.any():
        return None
    return float(np.mean(np.sign(actual[mask]) == np.sign(predicted[mask])))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a leakage-safe rolling GEXY walk-forward baseline using delta-only features. "
            "Each prediction uses only labels known strictly before that timestamp, fits on a "
            "recent rolling window, and chooses prediction shrinkage on a purged inner validation "
            "slice. Zero/no-move is always an allowed fallback."
        )
    )
    parser.add_argument("--features-csv", required=True, type=Path)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 5, 15, 30, 60))
    parser.add_argument("--window-rows", type=int, default=180)
    parser.add_argument("--validation-rows", type=int, default=30)
    parser.add_argument("--min-fit-rows", type=int, default=40)
    parser.add_argument("--alpha", type=float, default=100.0)
    parser.add_argument("--prediction-quantile", type=float, default=0.99)
    parser.add_argument("--min-validation-improvement-pct", type=float, default=5.0)
    args = parser.parse_args()

    if args.window_rows <= args.validation_rows:
        raise SystemExit("--window-rows must exceed --validation-rows")
    if args.min_fit_rows < 10:
        raise SystemExit("--min-fit-rows must be at least 10")

    raw = _ensure_backward_return(pd.read_csv(args.features_csv))
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce")

    summary_rows: list[dict[str, object]] = []
    all_predictions: list[pd.DataFrame] = []

    print(f"INPUT FEATURE ROWS: {len(raw)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"ROLLING HISTORY: {args.window_rows} rows")
    print(f"INNER VALIDATION: {args.validation_rows} rows with horizon purge")
    print(f"DELTA-ONLY FEATURES REQUESTED: {len(DELTA_ONLY_FEATURES)}")
    print(f"RIDGE ALPHA: {args.alpha:g}")
    print(f"NO-EDGE GATE: require >= {args.min_validation_improvement_pct:.1f}% validation MAE improvement vs zero")

    for horizon in args.horizons:
        prepared, features, target = prepare_baseline_frame(
            raw,
            horizon_minutes=horizon,
            feature_candidates=DELTA_ONLY_FEATURES,
        )
        records: list[dict[str, object]] = []
        skipped_short_history = 0
        skipped_inner_split = 0

        for _, current in prepared.iterrows():
            prediction_time = pd.Timestamp(current["timestamp"])
            history = eligible_history(
                prepared,
                prediction_time=prediction_time,
                horizon_minutes=horizon,
                max_rows=args.window_rows,
            )
            if len(history) < args.validation_rows + args.min_fit_rows:
                skipped_short_history += 1
                continue
            try:
                inner = inner_purged_split(
                    history,
                    horizon_minutes=horizon,
                    validation_rows=args.validation_rows,
                    min_fit_rows=args.min_fit_rows,
                )
            except ValueError:
                skipped_inner_split += 1
                continue

            fit_model = fit_stationary_ridge(
                inner.fit,
                features=features,
                target=target,
                alpha=args.alpha,
                prediction_quantile=args.prediction_quantile,
            )
            validation_actual = pd.to_numeric(inner.validation[target], errors="coerce")
            validation_raw = fit_model.predict(inner.validation)
            choice = choose_shrinkage(
                validation_actual,
                validation_raw,
                min_improvement_pct=args.min_validation_improvement_pct,
            )

            full_model = fit_stationary_ridge(
                history,
                features=features,
                target=target,
                alpha=args.alpha,
                prediction_quantile=args.prediction_quantile,
            )
            raw_prediction = float(full_model.predict(pd.DataFrame([current]))[0])
            prediction = float(choice.shrinkage * raw_prediction)
            actual = float(current[target])
            momentum = float(current.get("backward_return_1m_bps", 0.0))
            if not np.isfinite(momentum):
                momentum = 0.0

            records.append(
                {
                    "timestamp": prediction_time,
                    "horizon_minutes": horizon,
                    "actual_forward_return_bps": actual,
                    "rolling_prediction_bps": prediction,
                    "raw_model_prediction_bps": raw_prediction,
                    "selected_shrinkage": choice.shrinkage,
                    "validation_improvement_pct": choice.improvement_pct,
                    "validation_model_mae_bps": choice.validation_mae_bps,
                    "validation_zero_mae_bps": choice.zero_mae_bps,
                    "zero_prediction_bps": 0.0,
                    "momentum_prediction_bps": momentum,
                    "history_rows": len(history),
                    "inner_fit_rows": len(inner.fit),
                    "inner_validation_rows": len(inner.validation),
                }
            )

        if not records:
            print(f"\nHORIZON {horizon}m: no walk-forward predictions built")
            continue

        predictions = pd.DataFrame(records)
        all_predictions.append(predictions)
        actual = predictions["actual_forward_return_bps"].to_numpy(dtype=float)
        rolling = predictions["rolling_prediction_bps"].to_numpy(dtype=float)
        zero = predictions["zero_prediction_bps"].to_numpy(dtype=float)
        momentum = predictions["momentum_prediction_bps"].to_numpy(dtype=float)

        rolling_metrics = evaluate_predictions(actual, rolling)
        zero_metrics = evaluate_predictions(actual, zero)
        momentum_metrics = evaluate_predictions(actual, momentum)
        mae_vs_zero = (
            (rolling_metrics.mae_bps / zero_metrics.mae_bps - 1.0) * 100.0
            if zero_metrics.mae_bps > 0
            else float("nan")
        )
        active = predictions["selected_shrinkage"].to_numpy(dtype=float) > 0
        active_pct = float(np.mean(active) * 100.0)
        active_dir = _directional_accuracy_active(actual, rolling)
        mean_shrinkage = float(predictions["selected_shrinkage"].mean())

        summary_rows.append(
            {
                "horizon_minutes": horizon,
                "predictions": len(predictions),
                "rolling_mae_bps": rolling_metrics.mae_bps,
                "rolling_rmse_bps": rolling_metrics.rmse_bps,
                "rolling_correlation": rolling_metrics.correlation,
                "rolling_directional_accuracy_all": rolling_metrics.directional_accuracy,
                "active_prediction_pct": active_pct,
                "active_directional_accuracy": active_dir,
                "mean_selected_shrinkage": mean_shrinkage,
                "rolling_mae_vs_zero_pct": mae_vs_zero,
                "zero_mae_bps": zero_metrics.mae_bps,
                "momentum_mae_bps": momentum_metrics.mae_bps,
                "momentum_directional_accuracy": momentum_metrics.directional_accuracy,
                "skipped_short_history": skipped_short_history,
                "skipped_inner_split": skipped_inner_split,
            }
        )

        print(f"\nHORIZON {horizon}m")
        print(f"WALK-FORWARD PREDICTIONS: {len(predictions)}")
        print(f"ACTIVE NONZERO FORECASTS: {active_pct:.1f}%")
        print(f"MEAN SELECTED SHRINKAGE: {mean_shrinkage:.3f}")
        print(
            f"ROLLING: MAE={rolling_metrics.mae_bps:.3f}bps "
            f"RMSE={rolling_metrics.rmse_bps:.3f}bps "
            f"CORR={rolling_metrics.correlation if rolling_metrics.correlation is not None else float('nan'):.4f} "
            f"MAE-vs-ZERO={mae_vs_zero:+.1f}%"
        )
        print(f"NO-MOVE: MAE={zero_metrics.mae_bps:.3f}bps")
        print(
            f"1M-MOMENTUM: MAE={momentum_metrics.mae_bps:.3f}bps "
            f"DIR={momentum_metrics.directional_accuracy if momentum_metrics.directional_accuracy is not None else float('nan'):.1%}"
        )
        print(
            "ACTIVE-ONLY DIRECTIONAL ACCURACY: "
            + (f"{active_dir:.1%}" if active_dir is not None else "n/a")
        )
        counts = predictions["selected_shrinkage"].value_counts().sort_index()
        print("SHRINKAGE COUNTS: " + ", ".join(f"{value:g}={count}" for value, count in counts.items()))

    if not summary_rows:
        raise SystemExit("no horizon produced walk-forward predictions")

    summary = pd.DataFrame(summary_rows)
    combined = pd.concat(all_predictions, ignore_index=True)
    stem = args.features_csv.stem
    summary_path = args.features_csv.with_name(f"{stem}_rolling_walkforward_summary.csv")
    prediction_path = args.features_csv.with_name(f"{stem}_rolling_walkforward_predictions.csv")
    summary.to_csv(summary_path, index=False)
    combined.to_csv(prediction_path, index=False)

    print("\nWALK-FORWARD SUMMARY")
    display = [
        "horizon_minutes",
        "predictions",
        "rolling_mae_bps",
        "rolling_rmse_bps",
        "rolling_correlation",
        "active_prediction_pct",
        "active_directional_accuracy",
        "mean_selected_shrinkage",
        "rolling_mae_vs_zero_pct",
        "zero_mae_bps",
        "momentum_mae_bps",
    ]
    print(summary[display].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED PREDICTIONS: {prediction_path}")
    print(
        "NOTE: Zero/no-move is an explicit no-edge fallback selected using only a recent inner "
        "validation slice. This single session is still a model-behavior diagnostic, not evidence "
        "of a durable trading edge."
    )


if __name__ == "__main__":
    main()
