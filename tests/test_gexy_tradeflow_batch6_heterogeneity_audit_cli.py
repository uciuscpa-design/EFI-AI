from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_batch6_heterogeneity_audit_cli_is_frozen_and_local() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gexy_tradeflow_batch6_heterogeneity_audit.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    normalized = " ".join(result.stdout.split())
    assert "Batch-6" in normalized
    assert "15m only" in normalized
    assert "leave-one-minute-out" in normalized
    assert "no market-data request" in normalized
    assert "Batch-6 verdict" in normalized


def test_batch6_heterogeneity_date_parser_preserves_first_seen_order() -> None:
    from scripts.gexy_tradeflow_batch6_heterogeneity_audit import _parse_dates

    assert _parse_dates("2026-07-24,2026-07-23,2026-07-22,2026-07-24") == (
        "2026-07-24",
        "2026-07-23",
        "2026-07-22",
    )
