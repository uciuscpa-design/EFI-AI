from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_tradeflow_extract_launches_directly_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_extract.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Read previously purchased GEXY TCBBO DBN files" in result.stdout
