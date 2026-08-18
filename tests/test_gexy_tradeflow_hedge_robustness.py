from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_hedge_robustness import (
    lowest_coverage_rows,
    matched_with_coverage,
    score_core_pair_sensitivity,
    score_hedge_lead_lag,
)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    timestamps = pd.date_range("2026-08-12T13:31:00Z", periods=8, freq="min")
    raw = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_net_signed_contracts": range(1, 9),
            "flow_signed_call_contracts": range(2, 10),
            "flow_signed_put_contracts": range(-8, 0),
        }
    )
    hedge = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_minute": timestamps - pd.Timedelta(minutes=1),
            "replay_match": [True] * 8,
            "hedge_greek_solved_pct": [0.9] * 7 + [0.0],
            "hedge_classified_contract_volume": [100.0] * 8,
            "hedge_greek_solved_contract_volume": [100.0] * 7 + [0.0],
            "hedge_greek_solved_contract_volume_pct": [1.0] * 7 + [0.0],
            "hedge_delta_units": range(1, 9),
            "hedge_call_delta_units": range(2, 10),
            "hedge_put_delta_units": range(-8, 0),
            "hedge_gamma_units_per_point": range(3, 11),
            "hedge_call_gamma_units_per_point": range(4, 12),
            "hedge_put_gamma_units_per_point": range(5, 13),
            "backward_return_1m_bps": range(10, 18),
            "forward_return_1m_bps": range(20, 28),
            "forward_return_5m_bps": range(30, 38),
        }
    )
    return raw, hedge


def test_volume_coverage_floor_removes_zero_coverage_row() -> None:
    raw, hedge = _frames()
    all_rows = matched_with_coverage(raw, hedge, min_volume_coverage=0.0)
    strict = matched_with_coverage(raw, hedge, min_volume_coverage=0.90)

    assert len(all_rows) == 8
    assert len(strict) == 7
    lowest = lowest_coverage_rows(raw, hedge, limit=1)
    assert float(lowest.iloc[0]["hedge_greek_solved_contract_volume_pct"]) == 0.0


def test_fixed_pair_sensitivity_scores_same_pair_by_family() -> None:
    raw, hedge = _frames()
    results = score_core_pair_sensitivity(
        raw,
        hedge,
        horizons_minutes=(1,),
        coverage_floors=(0.90,),
    )

    assert len(results) == 6
    net = results.loc[results["pair"] == "net_contracts_vs_delta"]
    assert set(net["family"]) == {"raw_flow", "hedge_flow"}
    assert set(net["observations"]) == {7}


def test_lead_lag_keeps_contemporaneous_and_forward_targets_separate() -> None:
    raw, hedge = _frames()
    results = score_hedge_lead_lag(
        raw,
        hedge,
        min_volume_coverage=0.90,
        horizons_minutes=(1, 5),
    )

    periods = set(results["period"])
    assert periods == {"contemporaneous_flow_minute", "forward_1m", "forward_5m"}
    assert set(results["observations"]) == {7}
