from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .prediction_journal import load_entries, summarize_entries


def build_journal_report(path: str | Path) -> dict[str, object]:
    entries = load_entries(path)
    summary = summarize_entries(entries)
    pending = [entry for entry in entries if not entry.resolved]
    resolved = [entry for entry in entries if entry.resolved]

    next_due = min((entry.due_at for entry in pending), default=None)
    by_regime: dict[str, dict[str, object]] = {}
    regimes = sorted({entry.prediction.regime for entry in entries})
    for regime in regimes:
        regime_entries = [entry for entry in entries if entry.prediction.regime == regime]
        regime_summary = summarize_entries(regime_entries)
        by_regime[regime] = asdict(regime_summary)

    return {
        "journal_path": str(Path(path)),
        "summary": asdict(summary),
        "next_due_at": None if next_due is None else next_due.isoformat(),
        "resolved_ids": [entry.prediction_id for entry in resolved[-10:]],
        "pending_ids": [entry.prediction_id for entry in pending[:10]],
        "by_regime": by_regime,
    }
