from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from .prediction_journal import PredictionJournalEntry


def due_now(
    entries: Iterable[PredictionJournalEntry],
    *,
    observed_at: datetime,
    tolerance_seconds: int = 90,
) -> list[PredictionJournalEntry]:
    if observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    if tolerance_seconds < 0:
        raise ValueError("tolerance_seconds must be non-negative")
    tolerance = timedelta(seconds=tolerance_seconds)
    return [
        entry
        for entry in entries
        if not entry.resolved
        and entry.due_at <= observed_at
        and observed_at - entry.due_at <= tolerance
    ]
