from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow_opening_control_stability import summarize_opening_control_days


def test_summarize_opening_control_days_tracks_sign_flips() -> None:
    frame = pd.DataFrame(
        {
            "trading_day": ["2026-08-04", "2026-08-05", "2026-08-06"],
            "hedge_target_spearman": [-0.4, -0.5, -0.2],
            "hedge_partial_controlling_momentum": [-0.3, -0.4, -0.1],
            "hedge_partial_controlling_raw": [-0.5, -0.6, -0.03],
            "hedge_partial_controlling_momentum_and_raw": [-0.45, -0.52, 0.12],
            "ordinary_to_both_sign_flip": [False, False, True],
        }
    )

    result = summarize_opening_control_days(frame).iloc[0]

    assert result["days"] == 3
    assert result["ordinary_negative_days"] == 3
    assert result["momentum_and_raw_negative_days"] == 2
    assert result["ordinary_to_both_sign_flip_days"] == 1
    assert result["ordinary_to_both_sign_flip_dates"] == "2026-08-06"


def test_opening_control_stability_cli_launches_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_opening_control_stability.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "15-minute GEXY net-delta control structure" in normalized
    assert "--min-volume-coverage" in result.stdout
    assert "market-data request" in normalized
