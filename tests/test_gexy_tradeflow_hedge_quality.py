from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.tradeflow_hedge_quality import aggregate_greek_volume_coverage


def test_volume_weighted_greek_coverage_uses_classified_contract_volume() -> None:
    frame = pd.DataFrame(
        {
            "flow_minute": [pd.Timestamp("2026-08-12T13:30:00Z")] * 4,
            "size": [10.0, 20.0, 30.0, 40.0],
            "signed_side": [1.0, -1.0, 0.0, 1.0],
            "hedge_greek_available": [True, False, True, True],
        }
    )

    result = aggregate_greek_volume_coverage(frame)
    row = result.iloc[0]

    # Classified volume excludes the unknown-side 30 contracts: 10 + 20 + 40 = 70.
    # Solved classified volume is 10 + 40 = 50.
    assert row["hedge_greek_solved_contract_volume"] == pytest.approx(50.0)
    assert row["hedge_greek_solved_contract_volume_pct"] == pytest.approx(50.0 / 70.0)
    assert row["timestamp"] == pd.Timestamp("2026-08-12T13:31:00Z")
