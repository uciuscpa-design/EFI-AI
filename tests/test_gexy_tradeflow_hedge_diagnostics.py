from __future__ import annotations

import pandas as pd

from packages.gexy.tradeflow_hedge_diagnostics import (
    align_raw_and_hedge_frames,
    best_family_rows,
    score_raw_vs_hedge,
)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    timestamps = pd.date_range("2026-08-12T13:31:00Z", periods=8, freq="min")
    raw = pd.DataFrame(
        {
            "timestamp": timestamps,
            "flow_contract_imbalance": [1, -1, 1, -1, 1, -1, 1, -1],
        }
    )
    hedge = pd.DataFrame(
        {
            "timestamp": timestamps,
            "replay_match": [True] * 8,
            "hedge_greek_solved_pct": [0.9] * 8,
            "hedge_delta_units": [-4, -3, -2, -1, 1, 2, 3, 4],
            "forward_return_1m_bps": [-8, -6, -4, -2, 2, 4, 6, 8],
        }
    )
    return raw, hedge


def test_align_raw_and_hedge_uses_common_timestamps_only() -> None:
    raw, hedge = _frames()
    extra = raw.iloc[[0]].copy()
    extra["timestamp"] = pd.Timestamp("2026-08-12T13:30:00Z")
    raw = pd.concat([extra, raw], ignore_index=True)

    aligned = align_raw_and_hedge_frames(raw, hedge)

    assert len(aligned) == 8
    assert aligned["timestamp"].min() == pd.Timestamp("2026-08-12T13:31:00Z")
    assert "forward_return_1m_bps" in aligned.columns
    assert "flow_contract_imbalance" in aligned.columns


def test_score_raw_vs_hedge_scores_same_observations_and_identifies_stronger_hedge() -> None:
    raw, hedge = _frames()

    results = score_raw_vs_hedge(raw, hedge, horizons_minutes=(1,))
    best = best_family_rows(results)

    raw_best = best.loc[best["family"] == "raw_flow"].iloc[0]
    hedge_best = best.loc[best["family"] == "hedge_flow"].iloc[0]
    assert raw_best["observations"] == 8
    assert hedge_best["observations"] == 8
    assert hedge_best["signal"] == "hedge_delta_units"
    assert hedge_best["spearman"] == 1.0
    assert hedge_best["abs_spearman"] > raw_best["abs_spearman"]
