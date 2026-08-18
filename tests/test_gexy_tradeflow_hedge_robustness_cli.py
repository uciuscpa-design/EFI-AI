from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_tradeflow_hedge_robustness_launches_directly_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_hedge_robustness.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "hedge-flow robustness checks" in result.stdout
