from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_window_regime_cli_launches_directly_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_window_regime.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "opening and closing windows" in normalized
    assert "--min-volume-coverage" in result.stdout
    assert "market-data request" in normalized
