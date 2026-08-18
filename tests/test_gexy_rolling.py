from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.rolling import (
    DELTA_FEATURE_GROUPS,
    DELTA_ONLY_FEATURES,
    choose_shrinkage,
    eligible_history,
    inner_purged_split,
)


def _frame(rows: int = 240) -> pd.DataFrame:
    ts = pd.date_range("2026-08-13T13:31:00Z", periods=rows, freq="1min")
    x = np.linspace(-2.0, 2.0, rows)
    return pd.DataFrame(
        {
            "timestamp": ts,
            "backward_return_1m_bps": x,
            "forward_return_30m_bps": 0.5 * x,
        }
    )


def test_eligible_history_uses_only_labels_known_before_prediction() -> None:
    frame = _frame()
    prediction_time = pd.Timestamp("2026-08-13T17:00:00Z")
    history = eligible_history(
        frame,
        prediction_time=prediction_time,
        horizon_minutes=30,
        max_rows=180,
    )

    assert len(history) <= 180
    assert pd.to_datetime(history["timestamp"], utc=True).max() + pd.Timedelta(minutes=30) < prediction_time


def test_eligible_history_allows_only_matured_same_day_labels() -> None:
    frame = _frame(120)
    prediction_time = pd.Timestamp("2026-08-13T15:01:00Z")
    history = eligible_history(
        frame,
        prediction_time=prediction_time,
        horizon_minutes=30,
        max_rows=180,
    )

    timestamps = pd.to_datetime(history["timestamp"], utc=True)
    assert not history.empty
    assert timestamps.max() == pd.Timestamp("2026-08-13T14:30:00Z")
    assert (timestamps + pd.Timedelta(minutes=30) < prediction_time).all()
    assert pd.Timestamp("2026-08-13T14:31:00Z") not in set(timestamps)


def test_inner_split_purges_overlap_with_validation() -> None:
    history = _frame(180)
    split = inner_purged_split(
        history,
        horizon_minutes=30,
        validation_rows=30,
        min_fit_rows=40,
    )

    assert len(split.validation) == 30
    assert pd.to_datetime(split.fit["timestamp"], utc=True).max() + pd.Timedelta(minutes=30) < split.validation_start


def test_shrinkage_can_abstain_when_model_does_not_beat_zero() -> None:
    actual = np.array([0.5, -0.5, 0.25, -0.25])
    raw = np.array([5.0, 5.0, -5.0, -5.0])
    choice = choose_shrinkage(actual, raw, min_improvement_pct=5.0)

    assert choice.shrinkage == 0.0
    assert choice.validation_mae_bps == choice.zero_mae_bps


def test_shrinkage_allows_signal_when_validation_improves_materially() -> None:
    actual = np.array([1.0, 2.0, -1.0, -2.0])
    raw = actual.copy()
    choice = choose_shrinkage(actual, raw, min_improvement_pct=5.0)

    assert choice.shrinkage > 0.0
    assert choice.validation_mae_bps < choice.zero_mae_bps


def test_feature_groups_partition_frozen_delta_only_features() -> None:
    component_names = tuple(name for name in DELTA_FEATURE_GROUPS if name != "combined")
    flattened = tuple(feature for name in component_names for feature in DELTA_FEATURE_GROUPS[name])

    assert flattened == DELTA_ONLY_FEATURES
    assert DELTA_FEATURE_GROUPS["combined"] == DELTA_ONLY_FEATURES
    assert len(flattened) == len(set(flattened))
