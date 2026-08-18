from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def test_chronological_drift_cli_is_posthoc_local_and_holdout_safe() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_chronological_drift.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "Post-hoc descriptive" in normalized
    assert "17 already-seen dates" in normalized
    assert "5-session rolling medians" in normalized
    assert "no predictor" in normalized
    assert "no reserved holdout date" in normalized
    assert "no market-data request" in normalized


def test_chronological_drift_dates_and_holdout_are_exact() -> None:
    from scripts.gexy_tradeflow_chronological_drift import (
        CHRONOLOGICAL_DATES,
        RESERVED_HOLDOUT_DATES,
        ROLLING_WINDOW,
    )

    assert CHRONOLOGICAL_DATES == (
        "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-27", "2026-07-28",
        "2026-07-29", "2026-07-30", "2026-07-31", "2026-08-03", "2026-08-04",
        "2026-08-05", "2026-08-06", "2026-08-07", "2026-08-10", "2026-08-11",
        "2026-08-12", "2026-08-13",
    )
    assert RESERVED_HOLDOUT_DATES == ("2026-07-21", "2026-07-20", "2026-07-17")
    assert ROLLING_WINDOW == 5


def test_sign_run_summary_is_deterministic() -> None:
    from scripts.gexy_tradeflow_chronological_drift import _sign_run_summary

    summary = _sign_run_summary(pd.Series([-1.0, 2.0, -3.0, -4.0, 5.0, 6.0, -1.0]))
    assert summary["sign_runs"] == 5
    assert summary["longest_negative_run"] == 2
    assert summary["longest_positive_run"] == 2
    assert summary["terminal_run_sign"] == "negative"
    assert summary["terminal_run_length"] == 1


def test_trend_summary_reports_stable_negative_example() -> None:
    from scripts.gexy_tradeflow_chronological_drift import _trend_summary

    frame = pd.DataFrame(
        {
            "ordinary_spearman": [0.5, 0.4, 0.3, 0.2, 0.1, -0.1],
        }
    )
    summary = _trend_summary(frame)
    assert np.isfinite(summary["trend_spearman"])
    assert summary["trend_spearman"] < 0
    assert summary["trend_loo_count"] == 6
    assert summary["trend_loo_same_sign_count"] == 6
    assert summary["trend_loo_any_opposite_sign"] is False
