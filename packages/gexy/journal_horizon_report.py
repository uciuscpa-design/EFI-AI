from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .horizon_metrics import summarize_by_horizon
from .journal_report import build_journal_report
from .prediction_journal import load_entries


def build_journal_horizon_report(path: str | Path) -> dict[str, object]:
    report = dict(build_journal_report(path))
    entries = load_entries(path)
    report["by_horizon"] = {
        str(metrics.horizon_minutes): asdict(metrics)
        for metrics in summarize_by_horizon(entries)
    }
    return report
