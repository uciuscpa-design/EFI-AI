from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np


def test_cumulative_heterogeneity_cli_is_frozen_local_and_holdout_safe() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_cumulative_heterogeneity_characterization.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "17 already-seen dates" in normalized
    assert "leave-one-minute-out" in normalized
    assert "no predictor" in normalized
    assert "no reserved holdout date" in normalized
    assert "no market-data request" in normalized


def test_cumulative_heterogeneity_frozen_dates_are_exact() -> None:
    from scripts.gexy_tradeflow_cumulative_heterogeneity_characterization import (
        FROZEN_DATES,
        RESERVED_HOLDOUT_DATES,
    )

    assert FROZEN_DATES == (
        "2026-08-13", "2026-08-12", "2026-08-11", "2026-08-10", "2026-08-07",
        "2026-08-06", "2026-08-05", "2026-08-04", "2026-08-03", "2026-07-31",
        "2026-07-30", "2026-07-29", "2026-07-28", "2026-07-27", "2026-07-24",
        "2026-07-23", "2026-07-22",
    )
    assert RESERVED_HOLDOUT_DATES == ("2026-07-21", "2026-07-20", "2026-07-17")


def test_cumulative_heterogeneity_strict_stability_categories() -> None:
    from scripts.gexy_tradeflow_cumulative_heterogeneity_characterization import _classify

    category, count, pct = _classify(-0.2, np.array([-0.3, -0.1, -0.05]))
    assert category == "strict_sign_stable_negative"
    assert count == 3
    assert pct == 1.0

    category, count, pct = _classify(0.2, np.array([0.3, 0.1, 0.05]))
    assert category == "strict_sign_stable_positive"
    assert count == 3
    assert pct == 1.0

    category, count, pct = _classify(-0.2, np.array([-0.3, 0.01, -0.05]))
    assert category == "sign_fragile"
    assert count == 2
    assert pct == 2 / 3
