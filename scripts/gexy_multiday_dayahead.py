from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from packages.gexy.baseline import evaluate_predictions, fit_stationary_ridge, prepare_baseline_frame
from packages.gexy.rolling import DELTA_ONLY_FEATURES, choose_shrinkage, inner_purged_split


NY = ZoneInfo("America/New_York")

# Frozen V3 research settings. Intentionally not exposed as CLI tuning knobs in
# this strict day-ahead evaluator so the multi-session result cannot be tuned
# against the newly acquired dates by accident.
WINDOW_ROWS = 180
VALIDATION_ROWS = 30
MIN_FIT_ROWS = 40
RIDGE_ALPHA = 100.0
PREDICTION_QUANTILE = 0.99
MIN_VALIDATION_IMPROVEMENT_PCT = 5.0


def _parse_dates(value: str) -> tuple[date, ...]:
    days = tuple(sorted({date.fromisoformat(item.strip()) for item in value.split(",") if item.strip()}))
    if len(days) < 2:
        raise argparse.ArgumentTypeError("--dates must contain at least two ISO dates")
    return days


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(item < 1 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive minutes")
    return horizons


def _features_path(day: date) -> Path:
    return Path(f"gexy_spxw_{day.isoformat()}_replay_features.csv")


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


def _active_directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    mask = np.isfinite(actual) & np.isfinite(predicted) & (predicted != 0) & (actual != 0)
    if not mask.any():
        return None
    return float(np.mean(np.sign(actual[mask]) == np.sign(predicted[mask])))


def _load_sessions(days: tuple[date, ...]) -> pd.DataFrame:
    sessions: list[pd.DataFrame] = []
    for day in days:
        path = _features_path(day)
        if not path.exists():
            raise SystemExit(f"missing replay feature CSV: {path}")
        frame = _ensure_backward_return(pd.read_csv(path))
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
        frame["session_date"] = day.isoformat()
        sessions.append(frame)
    return pd.concat(sessions, ignore_index=True, sort=False).sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run strict date-blocked GEXY V3 validation. Each test session is predicted using only "
            "earlier sessions. The V3 feature set and hyperparameters are frozen; no labels from "
            "the test date enter model fitting, preprocessing, prediction caps, or shrinkage choice."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--horizons", default=(1, 5, 15, 30, 60), type=_parse_horizons)
    args = parser.parse_args()

    raw = _load_sessions(args.dates)
    raw["session_date"] = pd.to_datetime(raw["timestamp"], utc=True).dt.tz_convert(NY).dt.date.astype(str)

    print("STRICT MULTI-SESSION DAY-AHEAD VALIDATION")
    print(f"SESSIONS: {len(args.dates)}")
    print(f"WARMUP SESSION: {args.dates[0].isoformat()} (not scored)")
    print(f"TEST SESSIONS: {len(args.dates) - 1}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"FROZEN WINDOW ROWS: {WINDOW_ROWS}")
    print(f"FROZEN INNER VALIDATION ROWS: {VALIDATION_ROWS}")
    print(f"FROZEN RIDGE ALPHA: {RIDGE_ALPHA:g}")
    print(f"FROZEN NO-EDGE GATE: >= {MIN_VALIDATION_IMPROVEMENT_PCT:.1f}% validation MAE improvement vs zero")
    print("TEST-DAY LABELS USED FOR TRAINING: NO")

    day_rows: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    aggregate_rows: list[dict[str, object]] = []

    for horizon in args.horizons:
        prepared, features, target = prepare_baseline_frame(
            raw,
            horizon_minutes=horizon,
            feature_candidates=DELTA_ONLY_FEATURES,
        )
        prepared["session_date"] = (
            pd.to_datetime(prepared["timestamp"], utc=True).dt.tz_convert(NY).dt.date.astype(str)
        )
        horizon_predictions: list[pd.DataFrame] = []

        for test_day in args.dates[1:]:
            test_day_text = test_day.isoformat()
            history = prepared.loc[prepared["session_date"] < test_day_text].tail(WINDOW_ROWS).copy()
            test = prepared.loc[prepared["session_date"] == test_day_text].copy()
            if test.empty:
                print(f"HORIZON {horizon}m {test_day_text}: no labeled test rows; skipped")
                continue
            if len(history) < VALIDATION_ROWS + MIN_FIT_ROWS:
                print(
                    f"HORIZON {horizon}m {test_day_text}: only {len(history)} prior-session rows; skipped"
                )
                continue

            try:
                inner = inner_purged_split(
                    history,
                    horizon_minutes=horizon,
                    validation_rows=VALIDATION_ROWS,
                    min_fit_rows=MIN_FIT_ROWS,
                )
            except ValueError as exc:
                print(f"HORIZON {horizon}m {test_day_text}: prior-session inner split failed: {exc}")
                continue

            gate_model = fit_stationary_ridge(
                inner.fit,
                features=features,
                target=target,
                alpha=RIDGE_ALPHA,
                prediction_quantile=PREDICTION_QUANTILE,
            )
            validation_actual = pd.to_numeric(inner.validation[target], errors="coerce")
            validation_raw = gate_model.predict(inner.validation)
            choice = choose_shrinkage(
                validation_actual,
                validation_raw,
                min_improvement_pct=MIN_VALIDATION_IMPROVEMENT_PCT,
            )

            model = fit_stationary_ridge(
                history,
                features=features,
                target=target,
                alpha=RIDGE_ALPHA,
                prediction_quantile=PREDICTION_QUANTILE,
            )
            raw_prediction = model.predict(test)
            prediction = choice.shrinkage * raw_prediction
            actual = pd.to_numeric(test[target], errors="coerce").to_numpy(dtype=float)
            momentum = pd.to_numeric(test["backward_return_1m_bps"], errors="coerce").fillna(0.0).to_numpy(dtype=float)
            zero = np.zeros(len(test), dtype=float)

            rolling_metrics = evaluate_predictions(actual, prediction)
            zero_metrics = evaluate_predictions(actual, zero)
            momentum_metrics = evaluate_predictions(actual, momentum)
            mae_vs_zero = (
                (rolling_metrics.mae_bps / zero_metrics.mae_bps - 1.0) * 100.0
                if zero_metrics.mae_bps > 0
                else float("nan")
            )
            active_dir = _active_directional_accuracy(actual, prediction)
            active_pct = float(np.mean(prediction != 0) * 100.0)

            day_rows.append(
                {
                    "session_date": test_day_text,
                    "horizon_minutes": horizon,
                    "test_rows": len(test),
                    "prior_history_rows": len(history),
                    "features_used": len(model.features),
                    "selected_shrinkage": choice.shrinkage,
                    "validation_improvement_pct": choice.improvement_pct,
                    "dayahead_mae_bps": rolling_metrics.mae_bps,
                    "dayahead_rmse_bps": rolling_metrics.rmse_bps,
                    "dayahead_correlation": rolling_metrics.correlation,
                    "dayahead_directional_accuracy_all": rolling_metrics.directional_accuracy,
                    "active_prediction_pct": active_pct,
                    "active_directional_accuracy": active_dir,
                    "mae_vs_zero_pct": mae_vs_zero,
                    "zero_mae_bps": zero_metrics.mae_bps,
                    "momentum_mae_bps": momentum_metrics.mae_bps,
                    "momentum_directional_accuracy": momentum_metrics.directional_accuracy,
                }
            )

            output = pd.DataFrame(
                {
                    "timestamp": test["timestamp"].to_numpy(),
                    "session_date": test_day_text,
                    "horizon_minutes": horizon,
                    "actual_forward_return_bps": actual,
                    "dayahead_prediction_bps": prediction,
                    "raw_model_prediction_bps": raw_prediction,
                    "selected_shrinkage": choice.shrinkage,
                    "validation_improvement_pct": choice.improvement_pct,
                    "zero_prediction_bps": 0.0,
                    "momentum_prediction_bps": momentum,
                }
            )
            horizon_predictions.append(output)
            prediction_frames.append(output)

            active_text = f"{active_dir:.1%}" if active_dir is not None else "n/a"
            print(
                f"HORIZON {horizon}m {test_day_text}: shrink={choice.shrinkage:g} "
                f"MAE={rolling_metrics.mae_bps:.3f} vs zero={zero_metrics.mae_bps:.3f} "
                f"({mae_vs_zero:+.2f}%) active-dir={active_text}"
            )

        if not horizon_predictions:
            continue

        combined = pd.concat(horizon_predictions, ignore_index=True)
        actual = combined["actual_forward_return_bps"].to_numpy(dtype=float)
        prediction = combined["dayahead_prediction_bps"].to_numpy(dtype=float)
        zero = combined["zero_prediction_bps"].to_numpy(dtype=float)
        momentum = combined["momentum_prediction_bps"].to_numpy(dtype=float)
        model_metrics = evaluate_predictions(actual, prediction)
        zero_metrics = evaluate_predictions(actual, zero)
        momentum_metrics = evaluate_predictions(actual, momentum)
        mae_vs_zero = (
            (model_metrics.mae_bps / zero_metrics.mae_bps - 1.0) * 100.0
            if zero_metrics.mae_bps > 0
            else float("nan")
        )
        active_dir = _active_directional_accuracy(actual, prediction)
        active_pct = float(np.mean(prediction != 0) * 100.0)
        horizon_day_rows = [row for row in day_rows if row["horizon_minutes"] == horizon]
        winning_days = sum(float(row["mae_vs_zero_pct"]) < 0 for row in horizon_day_rows)

        aggregate_rows.append(
            {
                "horizon_minutes": horizon,
                "scored_sessions": len(horizon_day_rows),
                "predictions": len(combined),
                "dayahead_mae_bps": model_metrics.mae_bps,
                "dayahead_rmse_bps": model_metrics.rmse_bps,
                "dayahead_correlation": model_metrics.correlation,
                "dayahead_directional_accuracy_all": model_metrics.directional_accuracy,
                "active_prediction_pct": active_pct,
                "active_directional_accuracy": active_dir,
                "mae_vs_zero_pct": mae_vs_zero,
                "zero_mae_bps": zero_metrics.mae_bps,
                "momentum_mae_bps": momentum_metrics.mae_bps,
                "momentum_directional_accuracy": momentum_metrics.directional_accuracy,
                "days_beating_zero": winning_days,
            }
        )

    if not aggregate_rows:
        raise SystemExit("no horizon produced strict day-ahead predictions")

    aggregate = pd.DataFrame(aggregate_rows)
    per_day = pd.DataFrame(day_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)

    summary_path = Path("gexy_spxw_multiday_dayahead_summary.csv")
    day_path = Path("gexy_spxw_multiday_dayahead_by_day.csv")
    prediction_path = Path("gexy_spxw_multiday_dayahead_predictions.csv")
    aggregate.to_csv(summary_path, index=False)
    per_day.to_csv(day_path, index=False)
    predictions.to_csv(prediction_path, index=False)

    print("\nSTRICT DAY-AHEAD SUMMARY")
    display = [
        "horizon_minutes",
        "scored_sessions",
        "predictions",
        "dayahead_mae_bps",
        "zero_mae_bps",
        "mae_vs_zero_pct",
        "active_prediction_pct",
        "active_directional_accuracy",
        "days_beating_zero",
        "dayahead_correlation",
    ]
    print(aggregate[display].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED BY-DAY RESULTS: {day_path}")
    print(f"SAVED PREDICTIONS: {prediction_path}")
    print(
        "NOTE: This is strict session-ahead validation. The first date is warmup only. For each "
        "scored date, all preprocessing, model fitting, prediction bounds, and no-edge shrinkage "
        "selection use only earlier sessions. Test-day labels never enter the model."
    )


if __name__ == "__main__":
    main()
