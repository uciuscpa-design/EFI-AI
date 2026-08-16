from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_opening_validation_cli_launches_directly_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_opening_validation.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "opening-window validation endpoints" in normalized
    assert "Primary is opening 15m" in normalized
    assert "--min-volume-coverage" in result.stdout
    assert "market-data request" in normalized
