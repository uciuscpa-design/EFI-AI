from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_incremental_hedge_cli_launches_directly_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_hedge_incremental.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized_help = " ".join(result.stdout.split())
    assert "Measure whether Greek-weighted GEXY hedge-flow proxies retain forward association" in normalized_help
    assert "--min-volume-coverage" in result.stdout
