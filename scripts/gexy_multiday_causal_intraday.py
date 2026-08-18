from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from packages.gexy.baseline import evaluate_predictions, fit_stationary_ridge, prepare_baseline_frame
from packages.gexy.rolling import DELTA_ONLY_FEATURES, choose_shrinkage, eligible_history, inner_purged_split


NY = ZoneInfo("America/New_York")

# Keep these identical to frozen V3. This evaluator changes only the information
# set: at each prediction timestamp it may use same-session rows whose forward
# labels are already fully known. No future/current-label information is used.
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


def _active_directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    mask = np.isfinite(actual) & np.isfinite(predicted) & (predicted != 0) & (actual != 0)
    if not mask.any():
        return None
    return float(np.mean(np.sign(actual[mask]) == np.sign(predicted[mask])))


def _mae_vs_zero_pct(model_mae: float, zero_mae: float) -> float:
    if zero_mae <= 0:
        return float("nan")
    return (model_mae / zero_mae - 1.0) * 100.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run frozen GEXY V3 with causal intraday adaptation. At every prediction timestamp, "
            "training and gating may use only rows whose forward label is fully known before that timestamp."
        )
    )
    parser.add_argument("--dates", required=True, type=_parse_dates)
    parser.add_argument("--horizons", default=(1, 5, 15, 30, 60), type=_parse_horizons)
    args = parser.parse_args()

    raw = _load_sessions(args.dates)
    raw["session_date"] = pd.to_datetime(raw["timestamp"], utc=True).dt.tz_convert(NY).dt.date.astype(str)

    print("FROZEN CAUSAL INTRADAY VALIDATION")
    print(f"SESSIONS: {len(args.dates)}")
    print(f"WARMUP SESSION: {args.dates[0].isoformat()} (not scored)")
    print(f"TEST SESSIONS: {len(args.dates) - 1}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print(f"FROZEN WINDOW ROWS: {WINDOW_ROWS}")
    print(f"FROZEN INNER VALIDATION ROWS: {VALIDATION_ROWS}")
    print(f"FROZEN RIDGE ALPHA: {RIDGE_ALPHA:g}")
    print(f"FROZEN NO-EDGE GATE: >= {MIN_VALIDATION_IMPROVEMENT_PCT:.1f}% validation MAE improvement vs zero")
    print("SAME-DAY HISTORY ALLOWED: YES, ONLY AFTER ITS LABEL IS FULLY KNOWN")
    print("FUTURE/CURRENT LABELS USED FOR TRAINING: NO")

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
            test = prepared.loc[prepared["session_date"] == test_day_text].copy()
            if test.empty:
                print(f"HORIZON {horizon}m {test_day_text}: no labeled rows; skipped")
                continue

            rows: list[dict[str, object]] = []
            for _, test_row in test.iterrows():
                prediction_time = pd.Timestamp(test_row["timestamp"])
                history = eligible_history(
                    prepared,
                    prediction_time=prediction_time,
                    horizon_minutes=horizon,
                    max_rows=WINDOW_ROWS,
                )
                if len(history) < VALIDATION_ROWS + MIN_FIT_ROWS:
                    continue

                try:
                    inner = inner_purged_split(
                        history,
                        horizon_minutes=horizon,
                        validation_rows=VALIDATION_ROWS,
                        min_fit_rows=MIN_FIT_ROWS,
                    )
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
                except ValueError:
                    continue

                one = test_row.to_frame().T
                raw_prediction = float(model.predict(one)[0])
                prediction = float(choice.shrinkage * raw_prediction)
                actual = float(pd.to_numeric(pd.Series([test_row[target]]), errors="coerce").iloc[0])
                if not np.isfinite(actual):
                    continue

                history_session_dates = pd.to_datetime(history["timestamp"], utc=True).dt.tz_convert(NY).dt.date.astype(str)
                same_day_history_rows = int((history_session_dates == test_day_text).sum())
                latest_history_time = pd.Timestamp(history.iloc[-1]["timestamp"])

                rows.append(
                    {
                        "timestamp": prediction_time,
                        "session_date": test_day_text,
                        "horizon_minutes": horizon,
                        "actual_forward_return_bps": actual,
                        "causal_prediction_bps": prediction,
                        "raw_model_prediction_bps": raw_prediction,
                        "selected_shrinkage": choice.shrinkage,
                        "validation_improvement_pct": choice.improvement_pct,
                        "history_rows": len(history),
                        "same_day_history_rows": same_day_history_rows,
                        "latest_history_timestamp": latest_history_time,
                    }
                )

            if not rows:
                print(f"HORIZON {horizon}m {test_day_text}: no causal predictions; skipped")
                continue

            output = pd.DataFrame(rows)
            actual = output["actual_forward_return_bps"].to_numpy(dtype=float)
            prediction = output["causal_prediction_bps"].to_numpy(dtype=float)
            zero = np.zeros(len(output), dtype=float)
            model_metrics = evaluate_predictions(actual, prediction)
            zero_metrics = evaluate_predictions(actual, zero)
            mae_vs_zero = _mae_vs_zero_pct(model_metrics.mae_bps, zero_metrics.mae_bps)
            active_pct = float(np.mean(prediction != 0) * 100.0)
            active_dir = _active_directional_accuracy(actual, prediction)
            active_text = f"{active_dir:.1%}" if active_dir is not None else "n/a"

            day_rows.append(
                {
                    "session_date": test_day_text,
                    "horizon_minutes": horizon,
                    "predictions": len(output),
                    "mae_bps": model_metrics.mae_bps,
                    "zero_mae_bps": zero_metrics.mae_bps,
                    "mae_vs_zero_pct": mae_vs_zero,
                    "rmse_bps": model_metrics.rmse_bps,
                    "correlation": model_metrics.correlation,
                    "active_prediction_pct": active_pct,
                    "active_directional_accuracy": active_dir,
                    "median_same_day_history_rows": float(output["same_day_history_rows"].median()),
                    "max_same_day_history_rows": int(output["same_day_history_rows"].max()),
                }
            )
            horizon_predictions.append(output)
            prediction_frames.append(output)
            print(
                f"HORIZON {horizon}m {test_day_text}: rows={len(output)} "
                f"MAE={model_metrics.mae_bps:.3f} vs zero={zero_metrics.mae_bps:.3f} "
                f"({mae_vs_zero:+.2f}%) active={active_pct:.1f}% active-dir={active_text}"
            )

        if not horizon_predictions:
            continue

        combined = pd.concat(horizon_predictions, ignore_index=True)
        actual = combined["actual_forward_return_bps"].to_numpy(dtype=float)
        prediction = combined["causal_prediction_bps"].to_numpy(dtype=float)
        zero = np.zeros(len(combined), dtype=float)
        model_metrics = evaluate_predictions(actual, prediction)
        zero_metrics = evaluate_predictions(actual, zero)
        relevant_days = [row for row in day_rows if row["horizon_minutes"] == horizon]
        aggregate_rows.append(
            {
                "horizon_minutes": horizon,
                "scored_sessions": len(relevant_days),
                "predictions": len(combined),
                "mae_bps": model_metrics.mae_bps,
                "zero_mae_bps": zero_metrics.mae_bps,
                "mae_vs_zero_pct": _mae_vs_zero_pct(model_metrics.mae_bps, zero_metrics.mae_bps),
                "rmse_bps": model_metrics.rmse_bps,
                "correlation": model_metrics.correlation,
                "active_prediction_pct": float(np.mean(prediction != 0) * 100.0),
                "active_directional_accuracy": _active_directional_accuracy(actual, prediction),
                "days_beating_zero": sum(float(row["mae_vs_zero_pct"]) < 0 for row in relevant_days),
                "days_active": sum(float(row["active_prediction_pct"]) > 0 for row in relevant_days),
            }
        )

    if not aggregate_rows:
        raise SystemExit("no horizon produced causal intraday predictions")

    aggregate = pd.DataFrame(aggregate_rows)
    per_day = pd.DataFrame(day_rows)
    predictions = pd.concat(prediction_frames, ignore_index=True)

    summary_path = Path("gexy_spxw_multiday_causal_intraday_summary.csv")
    day_path = Path("gexy_spxw_multiday_causal_intraday_by_day.csv")
    prediction_path = Path("gexy_spxw_multiday_causal_intraday_predictions.csv")
    aggregate.to_csv(summary_path, index=False)
    per_day.to_csv(day_path, index=False)
    predictions.to_csv(prediction_path, index=False)

    print("\nFROZEN CAUSAL INTRADAY SUMMARY")
    display = [
        "horizon_minutes",
        "scored_sessions",
        "predictions",
        "mae_bps",
        "zero_mae_bps",
        "mae_vs_zero_pct",
        "active_prediction_pct",
        "active_directional_accuracy",
        "days_active",
        "days_beating_zero",
        "correlation",
    ]
    print(aggregate[display].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED BY-DAY RESULTS: {day_path}")
    print(f"SAVED PREDICTIONS: {prediction_path}")
    print(
        "NOTE: This is causal intraday adaptation, not session-ahead validation. A scored day's earlier rows may "
        "enter history only after their full forward-return label would be known in real time. Hyperparameters, "
        "feature set, prediction cap, and no-edge gate remain frozen V3 settings."
    )


if __name__ == "__main__":
    main()
