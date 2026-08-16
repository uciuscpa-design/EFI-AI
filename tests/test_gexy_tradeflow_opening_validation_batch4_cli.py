from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_batch4_opening_validation_cli_is_15m_only_and_local() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_opening_validation_batch4.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "Batch-4" in normalized
    assert "15m only" in normalized
    assert "Endpoint A" in normalized
    assert "Endpoint B" in normalized
    assert "No 5m" in normalized
    assert "no market-data request" in normalized


def test_batch4_date_parser_preserves_first_seen_order() -> None:
    from scripts.gexy_tradeflow_opening_validation_batch4 import _parse_dates

    assert _parse_dates("2026-08-03,2026-07-31,2026-07-30,2026-08-03") == (
        "2026-08-03",
        "2026-07-31",
        "2026-07-30",
    )
