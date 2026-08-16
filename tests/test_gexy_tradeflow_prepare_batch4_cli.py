from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_batch4_prepare_cli_is_frozen_and_local_only() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_prepare_batch4.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "09:30-10:00" in normalized
    assert "+/-200" in normalized
    assert "15m labels" in normalized
    assert "does not evaluate validation endpoints" in normalized


def test_batch4_prepare_date_parser_preserves_order() -> None:
    from scripts.gexy_tradeflow_prepare_batch4 import _parse_dates

    assert _parse_dates("2026-08-03,2026-07-31,2026-07-30,2026-08-03") == (
        "2026-08-03",
        "2026-07-31",
        "2026-07-30",
    )
