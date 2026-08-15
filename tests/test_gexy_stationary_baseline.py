from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from packages.gexy.baseline import (
    STATIONARY_FEATURES,
    evaluate_predictions,
    fit_stationary_ridge,
)


def test_stationary_feature_set_excludes_monotonic_and_absolute_exposure_state() -> None:
    assert "time_to_expiry_minutes" not in STATIONARY_FEATURES
    assert "total_gax_forward_proxy_per_point" not in STATIONARY_FEATURES
    assert "total_unsigned_gex_forward_proxy_per_1pct" not in STATIONARY_FEATURES
    assert "heuristic_signed_gex_forward_proxy_per_1pct" not in STATIONARY_FEATURES
    assert "d_total_gax_forward_proxy_per_point" in STATIONARY_FEATURES
    assert "d_total_unsigned_gex_forward_proxy_per_1pct" in STATIONARY_FEATURES


def test_stationary_ridge_has_zero_intercept_and_caps_extrapolation() -> None:
    rows = 120
    x = np.linspace(-2.0, 2.0, rows)
    frame = pd.DataFrame(
        {
            "backward_return_1m_bps": x,
            "d_forward": x * 0.5,
            "forward_return_5m_bps": 2.0 * x,
        }
    )
    model = fit_stationary_ridge(
        frame,
        features=("backward_return_1m_bps", "d_forward"),
        target="forward_return_5m_bps",
        alpha=0.01,
        prediction_quantile=0.95,
    )

    assert model.target_mean == 0.0
    assert model.prediction_floor is not None
    assert model.prediction_ceiling is not None

    extreme = pd.DataFrame(
        {
            "backward_return_1m_bps": [1000.0],
            "d_forward": [500.0],
        }
    )
    predicted = model.predict(extreme)[0]
    assert predicted <= model.prediction_ceiling + 1e-12
    assert predicted >= model.prediction_floor - 1e-12


def test_stationary_ridge_recovers_simple_change_relationship() -> None:
    rows = 160
    x = np.linspace(-3.0, 3.0, rows)
    frame = pd.DataFrame(
        {
            "backward_return_1m_bps": x,
            "d_total_unsigned_gex_forward_proxy_per_1pct": x * 1_000_000.0,
            "forward_return_5m_bps": 1.5 * x,
        }
    )
    train = frame.iloc[:120]
    test = frame.iloc[120:]
    model = fit_stationary_ridge(
        train,
        features=(
            "backward_return_1m_bps",
            "d_total_unsigned_gex_forward_proxy_per_1pct",
        ),
        target="forward_return_5m_bps",
        alpha=0.1,
        prediction_quantile=1.0,
    )
    metrics = evaluate_predictions(test["forward_return_5m_bps"], model.predict(test))

    # Train-derived caps intentionally flatten the most extreme extrapolated
    # values, so correlation need not remain nearly perfect out of sample.
    # The synthetic relationship should still be strongly monotonic and retain
    # its direction everywhere.
    assert metrics.correlation is not None and metrics.correlation > 0.85
    assert metrics.directional_accuracy is not None and metrics.directional_accuracy > 0.95


def test_stationary_ridge_rejects_invalid_prediction_quantile() -> None:
    frame = pd.DataFrame(
        {
            "backward_return_1m_bps": [1.0, 2.0, 3.0],
            "forward_return_1m_bps": [1.0, 2.0, 3.0],
        }
    )
    with pytest.raises(ValueError, match="prediction_quantile"):
        fit_stationary_ridge(
            frame,
            features=("backward_return_1m_bps",),
            target="forward_return_1m_bps",
            prediction_quantile=0.5,
        )
