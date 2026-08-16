from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_batch4_heterogeneity_audit_cli_help() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_batch4_heterogeneity_audit.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "Batch-4 opening heterogeneity audit" in normalized
    assert "15m only" in normalized
    assert "leave-one-minute-out" in normalized
    assert "no market-data request" in normalized
