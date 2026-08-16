from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_batch4_heterogeneity import (
    HEDGE,
    MOMENTUM,
    RAW,
    TARGET,
    _contribution_summary,
    _loo_summary,
    _ols_residual,
)


def _sample() -> pd.DataFrame:
    n = 12
    hedge = np.arange(1, n + 1, dtype=float)
    target = -hedge + np.array([0.0, 0.2, -0.1, 0.1, 0.0, -0.2, 0.2, 0.0, -0.1, 0.1, 0.0, -0.1])
    return pd.DataFrame(
        {
            HEDGE: hedge,
            RAW: np.array([3, 1, 4, 2, 5, 7, 6, 9, 8, 10, 12, 11], dtype=float),
            MOMENTUM: np.array([0, 2, 1, 3, 5, 4, 7, 6, 9, 8, 11, 10], dtype=float),
            TARGET: target,
            "timestamp": pd.date_range("2026-08-03 13:31:00+00:00", periods=n, freq="min").astype(str),
        }
    )


def test_ols_rank_r2_exact_linear_fit() -> None:
    x = np.arange(1, 8, dtype=float).reshape(-1, 1)
    y = 2.0 * x[:, 0] + 3.0
    residual, r2 = _ols_residual(y, x)
    assert np.isclose(r2, 1.0, atol=1e-12)
    assert np.max(np.abs(residual)) < 1e-10


def test_ordinary_leave_one_out_negative_stability() -> None:
    sample = _sample()
    full_value = float(sample[HEDGE].rank().corr(sample[TARGET].rank()))
    summary = _loo_summary(sample, controlled=False, full_value=full_value)
    assert summary["loo_count"] == len(sample)
    assert summary["loo_negative_count"] == len(sample)
    assert summary["loo_negative_pct"] == 1.0
    assert summary["loo_any_sign_flip"] is False


def test_contribution_shares_are_ordered_and_bounded() -> None:
    summary = _contribution_summary(_sample(), controlled=False)
    one = float(summary["largest_abs_contribution_share"])
    three = float(summary["top3_abs_contribution_share"])
    five = float(summary["top5_abs_contribution_share"])
    assert 0.0 <= one <= three <= five <= 1.0
    assert summary["largest_abs_contribution_sign"] in {-1, 0, 1}
