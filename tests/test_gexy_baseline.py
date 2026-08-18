from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from packages.gexy.baseline import (
    evaluate_predictions,
    fit_ridge,
    prepare_baseline_frame,
    purged_chronological_split,
)


def _synthetic_frame(rows: int = 120) -> pd.DataFrame:
    timestamps = pd.date_range("2026-08-13T13:31:00Z", periods=rows, freq="1min")
    x = np.linspace(-2.0, 2.0, rows)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "backward_return_1m_bps": x,
            "d_forward": x * 0.5,
            "distance_to_unsigned_wall": 20.0 - x,
            "forward_return_5m_bps": 3.0 * x + 0.25,
        }
    )


def test_prepare_baseline_uses_requested_future_target_but_not_as_feature() -> None:
    prepared, features, target = prepare_baseline_frame(
        _synthetic_frame(), horizon_minutes=5
    )

    assert target == "forward_return_5m_bps"
    assert target not in features
    assert "backward_return_1m_bps" in features
    assert len(prepared) == 120


def test_purged_split_keeps_train_targets_before_test_start() -> None:
    prepared, _features, _target = prepare_baseline_frame(
        _synthetic_frame(), horizon_minutes=5
    )
    split = purged_chronological_split(
        prepared, horizon_minutes=5, train_fraction=0.70
    )

    assert split.train["timestamp"].max() + pd.Timedelta(minutes=5) < split.test_start
    assert split.test["timestamp"].min() == split.test_start


def test_ridge_recovers_simple_directional_relationship() -> None:
    prepared, features, target = prepare_baseline_frame(
        _synthetic_frame(), horizon_minutes=5
    )
    split = purged_chronological_split(
        prepared, horizon_minutes=5, train_fraction=0.70
    )
    model = fit_ridge(
        split.train,
        features=features,
        target=target,
        alpha=0.01,
    )
    predicted = model.predict(split.test)
    metrics = evaluate_predictions(split.test[target], predicted)

    assert metrics.correlation is not None and metrics.correlation > 0.99
    assert metrics.directional_accuracy is not None and metrics.directional_accuracy > 0.95
    assert metrics.mae_bps < 0.2


def test_split_rejects_tiny_dataset() -> None:
    prepared, _features, _target = prepare_baseline_frame(
        _synthetic_frame(rows=10), horizon_minutes=5
    )
    with pytest.raises(ValueError, match="20"):
        purged_chronological_split(prepared, horizon_minutes=5)
