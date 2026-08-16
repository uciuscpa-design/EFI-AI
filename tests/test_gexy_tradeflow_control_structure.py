from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_control_structure import score_control_structure


def test_score_control_structure_reports_fixed_control_paths() -> None:
    timestamps = pd.date_range("2026-08-06T13:31:00Z", periods=8, freq="min")
    raw = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_net_signed_contracts": [-4, -3, -2, -1, 1, 2, 3, 4],
        }
    )
    hedge = pd.DataFrame(
        {
            "timestamp": timestamps,
            "replay_match": True,
            "hedge_greek_solved_contract_volume_pct": 1.0,
            "hedge_delta_units": [-5, -4, -1, -2, 2, 1, 4, 5],
            "backward_return_1m_bps": [1, -1, 2, -2, 3, -3, 4, -4],
            "forward_return_5m_bps": [5, 4, 3, 2, -2, -3, -4, -5],
            "forward_return_15m_bps": [6, 5, 4, 3, -3, -4, -5, -6],
        }
    )

    result = score_control_structure(
        raw,
        hedge,
        trading_day="2026-08-06",
        horizons_minutes=(5, 15),
        min_volume_coverage=0.90,
    )

    assert result["horizon_minutes"].tolist() == [5, 15]
    assert (result["observations"] == 8).all()
    assert "hedge_partial_controlling_raw" in result.columns
    assert "hedge_partial_controlling_momentum_and_raw" in result.columns
    assert "ordinary_to_both_sign_flip" in result.columns
