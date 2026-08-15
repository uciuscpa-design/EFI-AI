from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# V3 intentionally uses only changes/rates known at the prediction timestamp.
# Level-like wall distances and concentration levels are excluded because the
# first 0DTE replay showed severe morning-to-afternoon distribution drift.
MOMENTUM_FEATURES = (
    "backward_return_1m_bps",
)

GEX_GAX_DYNAMICS_FEATURES = (
    "d_total_gax_forward_proxy_per_point",
    "d_total_unsigned_gex_forward_proxy_per_1pct",
    "d_heuristic_signed_gex_forward_proxy_per_1pct",
    "unsigned_gex_change_1m_pct",
)

WALL_MIGRATION_FEATURES = (
    "d_strongest_unsigned_wall",
    "d_strongest_positive_heuristic_wall",
    "d_strongest_negative_heuristic_wall",
)

CONCENTRATION_FEATURES = (
    "d_top1_unsigned_gex_concentration",
    "d_top5_unsigned_gex_concentration",
)

IV_SKEW_FEATURES = (
    "d_near_iv_skew_put_minus_call",
    "d_median_implied_volatility",
)

QUALITY_FEATURES = (
    "d_parity_median_abs_residual",
    "d_greeks_solved_pct",
)

DELTA_ONLY_FEATURES = (
    *MOMENTUM_FEATURES,
    *GEX_GAX_DYNAMICS_FEATURES,
    *WALL_MIGRATION_FEATURES,
    *CONCENTRATION_FEATURES,
    *IV_SKEW_FEATURES,
    *QUALITY_FEATURES,
)

DELTA_FEATURE_GROUPS = {
    "momentum": MOMENTUM_FEATURES,
    "gex_gax_dynamics": GEX_GAX_DYNAMICS_FEATURES,
    "wall_migration": WALL_MIGRATION_FEATURES,
    "concentration": CONCENTRATION_FEATURES,
    "iv_skew": IV_SKEW_FEATURES,
    "quality": QUALITY_FEATURES,
    "combined": DELTA_ONLY_FEATURES,
}


@dataclass(frozen=True)
class InnerSplit:
    fit: pd.DataFrame
    validation: pd.DataFrame
    validation_start: pd.Timestamp


@dataclass(frozen=True)
class ShrinkageChoice:
    shrinkage: float
    validation_mae_bps: float
    zero_mae_bps: float
    improvement_pct: float


def _chronological_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return a chronological frame plus UTC timestamps without needless re-sorts.

    Causal evaluators call the history helpers thousands of times against frames
    that are already timestamp-sorted.  The previous implementation sorted the
    entire frame on every call.  Preserve identical ordering semantics while
    taking the fast path when the caller already provides monotonic timestamps.
    """
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    if timestamps.is_monotonic_increasing:
        return frame, timestamps
    order = np.argsort(timestamps.to_numpy(), kind="stable")
    ordered = frame.iloc[order].copy()
    ordered_timestamps = timestamps.iloc[order]
    return ordered, ordered_timestamps


def eligible_history(
    frame: pd.DataFrame,
    *,
    prediction_time: pd.Timestamp,
    horizon_minutes: int,
    max_rows: int,
) -> pd.DataFrame:
    """Return recent rows whose future labels were fully known before prediction_time."""
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    horizon = pd.Timedelta(minutes=int(horizon_minutes))
    ordered, timestamps = _chronological_frame(frame)
    cutoff = pd.Timestamp(prediction_time) - horizon

    # Strictly preserve: timestamp + horizon < prediction_time.
    # searchsorted(..., side="left") returns the first timestamp >= cutoff,
    # therefore every row before end satisfies timestamp < cutoff.
    end = int(timestamps.searchsorted(cutoff, side="left"))
    start = max(0, end - max_rows)
    return ordered.iloc[start:end].copy().reset_index(drop=True)


def inner_purged_split(
    history: pd.DataFrame,
    *,
    horizon_minutes: int,
    validation_rows: int,
    min_fit_rows: int,
) -> InnerSplit:
    """Split recent history and purge fit labels that overlap validation start."""
    if validation_rows < 5:
        raise ValueError("validation_rows must be at least 5")
    if min_fit_rows < 10:
        raise ValueError("min_fit_rows must be at least 10")
    if len(history) <= validation_rows:
        raise ValueError("history is too short for validation split")

    ordered, timestamps = _chronological_frame(history)
    ordered = ordered.reset_index(drop=True)
    timestamps = timestamps.reset_index(drop=True)
    validation = ordered.tail(validation_rows).copy()
    validation_start = pd.Timestamp(validation.iloc[0]["timestamp"])
    horizon = pd.Timedelta(minutes=int(horizon_minutes))
    cutoff = validation_start - horizon

    # Strictly preserve: fit_timestamp + horizon < validation_start.
    fit_end = int(timestamps.searchsorted(cutoff, side="left"))
    fit = ordered.iloc[:fit_end].copy()
    if len(fit) < min_fit_rows:
        raise ValueError("purged inner split left too few fit rows")
    return InnerSplit(fit=fit, validation=validation, validation_start=validation_start)


def choose_shrinkage(
    actual: pd.Series | np.ndarray,
    raw_prediction: np.ndarray,
    *,
    candidates: tuple[float, ...] = (0.0, 0.1, 0.25, 0.5, 1.0),
    min_improvement_pct: float = 5.0,
) -> ShrinkageChoice:
    """Choose conservative prediction shrinkage on an inner validation slice.

    Zero is always available. A nonzero forecast is accepted only when it beats
    the no-move MAE by at least min_improvement_pct on the recent validation set.
    """
    y = np.asarray(actual, dtype=float)
    p = np.asarray(raw_prediction, dtype=float)
    mask = np.isfinite(y) & np.isfinite(p)
    y = y[mask]
    p = p[mask]
    if len(y) == 0:
        raise ValueError("no finite validation observations")
    if not candidates or any(item < 0 for item in candidates):
        raise ValueError("shrinkage candidates must be nonnegative")

    zero_mae = float(np.mean(np.abs(y)))
    scored: list[tuple[float, float]] = []
    for shrinkage in candidates:
        mae = float(np.mean(np.abs(float(shrinkage) * p - y)))
        scored.append((mae, float(shrinkage)))
    best_mae, best_shrinkage = min(scored, key=lambda item: (item[0], item[1]))

    if zero_mae <= 0:
        improvement = 0.0
        best_shrinkage = 0.0
        best_mae = zero_mae
    else:
        improvement = (zero_mae / best_mae - 1.0) * 100.0 if best_mae > 0 else float("inf")
        if best_shrinkage > 0 and improvement < float(min_improvement_pct):
            best_shrinkage = 0.0
            best_mae = zero_mae
            improvement = 0.0

    return ShrinkageChoice(
        shrinkage=best_shrinkage,
        validation_mae_bps=best_mae,
        zero_mae_bps=zero_mae,
        improvement_pct=improvement,
    )
