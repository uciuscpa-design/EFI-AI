from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_session_state_development_cli_is_frozen_local_and_holdout_safe() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_session_state_development.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "development-only" in normalized
    assert "09:40" in normalized
    assert "six frozen descriptors" in normalized
    assert "no market-data request" in normalized
    assert "reserved holdout dates are not read" in normalized


def test_session_state_frozen_date_sets_are_exact() -> None:
    from scripts.gexy_tradeflow_session_state_development import (
        FROZEN_DEVELOPMENT_DATES,
        RESERVED_HOLDOUT_DATES,
    )

    assert FROZEN_DEVELOPMENT_DATES == (
        "2026-08-13",
        "2026-08-12",
        "2026-08-11",
        "2026-08-10",
        "2026-08-07",
        "2026-08-06",
        "2026-08-05",
        "2026-08-04",
        "2026-08-03",
        "2026-07-31",
        "2026-07-30",
        "2026-07-29",
        "2026-07-28",
        "2026-07-27",
        "2026-07-24",
        "2026-07-23",
        "2026-07-22",
    )
    assert RESERVED_HOLDOUT_DATES == (
        "2026-07-21",
        "2026-07-20",
        "2026-07-17",
    )


def test_session_state_selects_at_most_one_highest_abs_eligible_candidate() -> None:
    from scripts.gexy_tradeflow_session_state_development import _select_candidate

    summary = pd.DataFrame(
        [
            {"descriptor": "weak", "abs_spearman": 0.20, "eligible": False},
            {"descriptor": "candidate_a", "abs_spearman": 0.44, "eligible": True},
            {"descriptor": "candidate_b", "abs_spearman": 0.51, "eligible": True},
        ]
    )
    assert _select_candidate(summary) == "candidate_b"

    none = pd.DataFrame(
        [
            {"descriptor": "weak_a", "abs_spearman": 0.34, "eligible": False},
            {"descriptor": "weak_b", "abs_spearman": 0.33, "eligible": False},
        ]
    )
    assert _select_candidate(none) is None
