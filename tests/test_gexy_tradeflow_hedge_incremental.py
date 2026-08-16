from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import partial_spearman, score_incremental_hedge_information


def test_partial_spearman_removes_relationship_explained_by_momentum() -> None:
    momentum = pd.Series(np.arange(1.0, 21.0))
    signal = momentum * 3.0
    target = momentum * -2.0

    n, value = partial_spearman(signal, target, pd.DataFrame({"momentum": momentum}))

    assert n == 20
    assert np.isnan(value)


def test_incremental_score_keeps_hedge_information_beyond_momentum_and_raw() -> None:
    n = 30
    timestamps = pd.date_range("2026-08-12T13:31:00Z", periods=n, freq="min")
    momentum = np.linspace(-2.0, 2.0, n)
    raw_signal = np.tile([-1.0, 0.0, 1.0], 10)
    hedge_signal = np.linspace(-3.0, 3.0, n) + np.tile([0.0, 2.0, -2.0], 10)
    target = 0.2 * momentum + 0.1 * raw_signal + hedge_signal

    raw = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_net_signed_contracts": raw_signal,
            "flow_signed_call_contracts": raw_signal,
            "flow_signed_put_contracts": raw_signal,
        }
    )
    hedge = pd.DataFrame(
        {
            "timestamp": timestamps,
            "replay_match": True,
            "hedge_greek_solved_contract_volume_pct": 1.0,
            "backward_return_1m_bps": momentum,
            "forward_return_5m_bps": target,
            "hedge_delta_units": hedge_signal,
            "hedge_call_delta_units": hedge_signal,
            "hedge_put_delta_units": hedge_signal,
        }
    )

    result = score_incremental_hedge_information(
        raw,
        hedge,
        min_volume_coverage=0.90,
        horizons_minutes=(5,),
    )
    row = result.loc[result["pair"] == "net_contracts_vs_delta"].iloc[0]

    assert row["observations"] == n
    assert row["hedge_spearman"] > 0.8
    assert row["hedge_partial_spearman_controlling_momentum_and_raw"] > 0.8
    assert bool(row["mechanical_sign_consistent"])
