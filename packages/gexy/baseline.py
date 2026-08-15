from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd


DEFAULT_FEATURES = (
    "backward_return_1m_bps",
    "d_forward",
    "total_gax_forward_proxy_per_point",
    "d_total_gax_forward_proxy_per_point",
    "total_unsigned_gex_forward_proxy_per_1pct",
    "d_total_unsigned_gex_forward_proxy_per_1pct",
    "heuristic_signed_gex_forward_proxy_per_1pct",
    "d_heuristic_signed_gex_forward_proxy_per_1pct",
    "unsigned_gex_change_1m_pct",
    "distance_to_unsigned_wall",
    "distance_to_positive_wall",
    "distance_to_negative_wall",
    "d_strongest_unsigned_wall",
    "d_strongest_positive_heuristic_wall",
    "d_strongest_negative_heuristic_wall",
    "top1_unsigned_gex_concentration",
    "top5_unsigned_gex_concentration",
    "median_implied_volatility",
    "near_iv_skew_put_minus_call",
    "parity_median_abs_residual",
    "greeks_solved_pct",
    "time_to_expiry_minutes",
)


@dataclass(frozen=True)
class RegressionMetrics:
    observations: int
    mae_bps: float
    rmse_bps: float
    correlation: float | None
    directional_accuracy: float | None


@dataclass(frozen=True)
class PurgedSplit:
    train: pd.DataFrame
    test: pd.DataFrame
    test_start: pd.Timestamp


@dataclass(frozen=True)
class RidgeFit:
    features: tuple[str, ...]
    medians: pd.Series
    means: pd.Series
    scales: pd.Series
    target_mean: float
    coefficients: np.ndarray
    alpha: float

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        values = _feature_matrix(frame, self.features, self.medians)
        standardized = (values - self.means.to_numpy(dtype=float)) / self.scales.to_numpy(dtype=float)
        return self.target_mean + standardized @ self.coefficients

    def standardized_coefficients(self) -> pd.Series:
        return pd.Series(self.coefficients, index=self.features, dtype="float64")


def target_column(horizon_minutes: int) -> str:
    horizon = int(horizon_minutes)
    if horizon < 1:
        raise ValueError("horizon must be positive")
    return f"forward_return_{horizon}m_bps"


def prepare_baseline_frame(
    frame: pd.DataFrame,
    *,
    horizon_minutes: int,
    feature_candidates: tuple[str, ...] = DEFAULT_FEATURES,
) -> tuple[pd.DataFrame, tuple[str, ...], str]:
    """Prepare a timestamped replay frame without using future-derived inputs."""
    if "timestamp" not in frame.columns:
        raise ValueError("baseline frame must contain timestamp")

    target = target_column(horizon_minutes)
    if target not in frame.columns:
        raise ValueError(f"baseline frame is missing target column {target}")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result[target] = pd.to_numeric(result[target], errors="coerce")
    result = result.dropna(subset=["timestamp", target]).sort_values("timestamp").reset_index(drop=True)

    features = tuple(feature for feature in feature_candidates if feature in result.columns)
    if not features:
        raise ValueError("none of the requested baseline features are present")

    for feature in features:
        result[feature] = pd.to_numeric(result[feature], errors="coerce")

    return result, features, target


def purged_chronological_split(
    frame: pd.DataFrame,
    *,
    horizon_minutes: int,
    train_fraction: float = 0.70,
) -> PurgedSplit:
    """Chronologically split and purge train labels that overlap the test period."""
    if not 0.5 <= train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0.5 and 1.0")
    if len(frame) < 20:
        raise ValueError("at least 20 labeled rows are required")

    ordered = frame.sort_values("timestamp").reset_index(drop=True)
    split_index = int(len(ordered) * train_fraction)
    split_index = min(max(split_index, 1), len(ordered) - 1)
    test_start = pd.Timestamp(ordered.loc[split_index, "timestamp"])
    horizon = pd.Timedelta(minutes=int(horizon_minutes))

    train = ordered.loc[ordered["timestamp"] + horizon < test_start].copy()
    test = ordered.loc[ordered["timestamp"] >= test_start].copy()
    if len(train) < 10 or len(test) < 5:
        raise ValueError("purged split left too few train or test rows")

    return PurgedSplit(train=train, test=test, test_start=test_start)


def fit_ridge(
    frame: pd.DataFrame,
    *,
    features: tuple[str, ...],
    target: str,
    alpha: float = 10.0,
) -> RidgeFit:
    """Fit a standardized ridge regression using train-only preprocessing."""
    if alpha < 0:
        raise ValueError("alpha must be nonnegative")

    usable_features: list[str] = []
    medians: dict[str, float] = {}
    means: dict[str, float] = {}
    scales: dict[str, float] = {}

    for feature in features:
        series = pd.to_numeric(frame[feature], errors="coerce")
        median_value = float(series.median()) if series.notna().any() else float("nan")
        if not np.isfinite(median_value):
            continue
        filled = series.fillna(median_value)
        mean_value = float(filled.mean())
        scale_value = float(filled.std(ddof=0))
        if not np.isfinite(scale_value) or scale_value <= 1e-12:
            continue
        usable_features.append(feature)
        medians[feature] = median_value
        means[feature] = mean_value
        scales[feature] = scale_value

    if not usable_features:
        raise ValueError("no nonconstant numeric features remain after train preprocessing")

    selected = tuple(usable_features)
    median_series = pd.Series(medians, index=selected, dtype="float64")
    mean_series = pd.Series(means, index=selected, dtype="float64")
    scale_series = pd.Series(scales, index=selected, dtype="float64")

    x = _feature_matrix(frame, selected, median_series)
    x = (x - mean_series.to_numpy(dtype=float)) / scale_series.to_numpy(dtype=float)
    y = pd.to_numeric(frame[target], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(y).all():
        raise ValueError("training target contains missing or non-finite values")

    target_mean = float(y.mean())
    centered_y = y - target_mean
    penalty = np.eye(x.shape[1], dtype=float) * float(alpha)
    coefficients = np.linalg.solve(x.T @ x + penalty, x.T @ centered_y)

    return RidgeFit(
        features=selected,
        medians=median_series,
        means=mean_series,
        scales=scale_series,
        target_mean=target_mean,
        coefficients=coefficients,
        alpha=float(alpha),
    )


def evaluate_predictions(actual: pd.Series | np.ndarray, predicted: np.ndarray) -> RegressionMetrics:
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)
    if y.shape != p.shape:
        raise ValueError("actual and predicted shapes must match")
    mask = np.isfinite(y) & np.isfinite(p)
    y = y[mask]
    p = p[mask]
    if len(y) == 0:
        raise ValueError("no finite predictions to evaluate")

    error = p - y
    mae = float(np.mean(np.abs(error)))
    rmse = sqrt(float(np.mean(error * error)))

    correlation: float | None = None
    if len(y) >= 2 and np.std(y) > 0 and np.std(p) > 0:
        correlation = float(np.corrcoef(y, p)[0, 1])

    nonzero = y != 0
    directional_accuracy: float | None = None
    if nonzero.any():
        directional_accuracy = float(np.mean(np.sign(p[nonzero]) == np.sign(y[nonzero])))

    return RegressionMetrics(
        observations=len(y),
        mae_bps=mae,
        rmse_bps=rmse,
        correlation=correlation,
        directional_accuracy=directional_accuracy,
    )


def _feature_matrix(frame: pd.DataFrame, features: tuple[str, ...], medians: pd.Series) -> np.ndarray:
    columns: list[np.ndarray] = []
    for feature in features:
        series = pd.to_numeric(frame[feature], errors="coerce")
        filled = series.fillna(float(medians[feature]))
        columns.append(filled.to_numpy(dtype=float))
    return np.column_stack(columns)
