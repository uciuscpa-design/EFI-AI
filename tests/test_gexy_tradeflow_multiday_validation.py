from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_multiday_validation import (
    fixed_clock_nonoverlap_sample,
    pooled_nonoverlap_primary,
    summarize_primary_days,
)


def test_summarize_primary_days_tracks_negative_sign_replication() -> None:
    frame = pd.DataFrame(
        {
            "horizon_minutes": [5, 5, 15, 15],
            "hedge_partial_spearman_controlling_momentum_and_raw": [-0.20, -0.18, -0.25, -0.20],
        }
    )

    result = summarize_primary_days(frame)

    five = result.loc[result["horizon_minutes"] == 5].iloc[0]
    fifteen = result.loc[result["horizon_minutes"] == 15].iloc[0]
    assert five["days"] == 2
    assert five["negative_days"] == 2
    assert bool(five["all_days_negative"])
    assert fifteen["median_partial_spearman"] == -0.225


def test_fixed_clock_nonoverlap_sample_uses_deterministic_horizon_grid() -> None:
    timestamps = pd.date_range("2026-08-13T13:31:00Z", periods=15, freq="min")
    raw = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_net_signed_contracts": range(15),
        }
    )
    hedge = pd.DataFrame(
        {
            "timestamp": timestamps,
            "replay_match": True,
            "hedge_greek_solved_contract_volume_pct": 1.0,
            "hedge_delta_units": range(15),
            "backward_return_1m_bps": range(15),
            "forward_return_5m_bps": range(15),
        }
    )

    result = fixed_clock_nonoverlap_sample(
        raw,
        hedge,
        horizon_minutes=5,
        min_volume_coverage=0.90,
    )

    assert result["timestamp"].dt.minute.tolist() == [35, 40, 45]


def test_pooled_nonoverlap_uses_categorical_day_fixed_effects() -> None:
    frames: list[tuple[str, pd.DataFrame, pd.DataFrame]] = []
    day_levels = [0.0, 10.0, 0.0]
    target_levels = [0.0, 20.0, 0.0]
    test_days = pd.date_range("2026-08-07T13:35:00Z", periods=3, freq="D")

    for day, signal_level, target_level in zip(test_days, day_levels, target_levels, strict=True):
        timestamps = pd.date_range(day, periods=3, freq="5min")
        raw = pd.DataFrame(
            {
                "timestamp": timestamps,
                "flow_net_signed_contracts": [0.0, 0.0, 0.0],
            }
        )
        hedge = pd.DataFrame(
            {
                "timestamp": timestamps,
                "replay_match": True,
                "hedge_greek_solved_contract_volume_pct": 1.0,
                "hedge_delta_units": [signal_level] * 3,
                "backward_return_1m_bps": [0.0, 0.0, 0.0],
                "forward_return_5m_bps": [target_level] * 3,
            }
        )
        frames.append((day.date().isoformat(), raw, hedge))

    result = pooled_nonoverlap_primary(frames, horizons_minutes=(5,), min_volume_coverage=0.90)

    assert len(result) == 1
    assert result.iloc[0]["observations"] == 9
    assert np.isnan(result.iloc[0]["partial_spearman_controlling_momentum_raw_and_day"])
