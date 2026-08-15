from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.replay import add_change_features, add_forward_horizon_labels


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-08-13T13:35:00Z",
                "2026-08-13T13:36:00Z",
                "2026-08-13T13:38:00Z",
            ],
            "forward": [7776.0, 7777.0, 7780.0],
            "total_gax_forward_proxy_per_point": [100.0, 110.0, 130.0],
            "total_unsigned_gex_forward_proxy_per_1pct": [1000.0, 1020.0, 1050.0],
            "heuristic_signed_gex_forward_proxy_per_1pct": [200.0, 250.0, 220.0],
            "strongest_unsigned_wall": [7800.0, 7800.0, 7810.0],
            "strongest_positive_heuristic_wall": [7800.0, 7800.0, 7810.0],
            "strongest_negative_heuristic_wall": [7725.0, 7725.0, 7730.0],
        }
    )


def test_change_features_compute_observation_deltas() -> None:
    result = add_change_features(_frame())

    assert result.loc[1, "d_forward"] == pytest.approx(1.0)
    assert result.loc[2, "d_total_gax_forward_proxy_per_point"] == pytest.approx(20.0)
    assert result.loc[2, "d_strongest_unsigned_wall"] == pytest.approx(10.0)
    assert result.loc[1, "unsigned_gex_change_1m_pct"] == pytest.approx(2.0)


def test_horizon_labels_require_exact_future_clock_minute() -> None:
    result = add_forward_horizon_labels(_frame(), [1, 2, 3])

    assert result.loc[0, "forward_t_plus_1m"] == pytest.approx(7777.0)
    assert pd.isna(result.loc[1, "forward_t_plus_1m"])
    assert result.loc[0, "forward_t_plus_3m"] == pytest.approx(7780.0)
    assert result.loc[0, "forward_move_3m_points"] == pytest.approx(4.0)


def test_horizon_labels_reject_nonpositive_horizon() -> None:
    with pytest.raises(ValueError, match="positive"):
        add_forward_horizon_labels(_frame(), [0])
