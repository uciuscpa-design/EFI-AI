from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_diagnostics import score_flow_signals


def test_score_flow_signals_filters_unmatched_rows_and_ranks_relationships() -> None:
    frame = pd.DataFrame(
        {
            "replay_match": [True, True, True, True, True, True, True, True, False],
            "flow_contract_imbalance": [-4, -3, -2, -1, 1, 2, 3, 4, 100],
            "flow_premium_imbalance": [4, 3, 2, 1, -1, -2, -3, -4, -100],
            "forward_return_1m_bps": [-8, -6, -4, -2, 2, 4, 6, 8, -999],
        }
    )

    results = score_flow_signals(
        frame,
        horizons_minutes=(1,),
        signal_columns=("flow_contract_imbalance", "flow_premium_imbalance"),
    )

    assert len(results) == 2
    contract = results.loc[results["signal"] == "flow_contract_imbalance"].iloc[0]
    premium = results.loc[results["signal"] == "flow_premium_imbalance"].iloc[0]
    assert contract["observations"] == 8
    assert contract["spearman"] == 1.0
    assert contract["directional_accuracy_same_sign"] == 1.0
    assert contract["top_minus_bottom_forward_bps"] > 0
    assert premium["spearman"] == -1.0
    assert premium["directional_accuracy_same_sign"] == 0.0


def test_score_flow_signals_skips_missing_horizon_and_signal_columns() -> None:
    frame = pd.DataFrame(
        {
            "replay_match": [True, True, True],
            "flow_contract_imbalance": [1.0, 2.0, 3.0],
            "forward_return_1m_bps": [0.5, 1.0, 1.5],
        }
    )

    results = score_flow_signals(
        frame,
        horizons_minutes=(1, 5),
        signal_columns=("flow_contract_imbalance", "missing_signal"),
    )

    assert len(results) == 1
    assert results.iloc[0]["horizon_minutes"] == 1
    assert results.iloc[0]["signal"] == "flow_contract_imbalance"
