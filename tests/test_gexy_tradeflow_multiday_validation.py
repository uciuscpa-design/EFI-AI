from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_multiday_validation import (
    fixed_clock_nonoverlap_sample,
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
