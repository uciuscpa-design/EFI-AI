from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .prediction_journal import JournalSummary, PredictionJournal, summarize_records


@dataclass(frozen=True)
class ResolveResult:
    due_count: int
    resolved_count: int
    summary: JournalSummary


def resolve_due_predictions(
    journal_path: str | Path,
    *,
    observation_time: datetime,
    observed_spot: float,
) -> ResolveResult:
    """Resolve journal entries whose forecast horizon has elapsed.

    The supplied observation is only applied to pending predictions with
    timestamp + horizon <= observation_time. Future/pending records are left
    untouched. This keeps resolution causal and avoids premature labeling.
    """
    if observed_spot <= 0:
        raise ValueError("observed_spot must be positive")
    if observation_time.tzinfo is None:
        observation_time = observation_time.replace(tzinfo=timezone.utc)

    journal = PredictionJournal(journal_path)
    records = journal.read_all()
    due_count = 0
    resolved_count = 0

    for record in records:
        if record.resolved_spot is not None:
            continue
        due_at = record.timestamp + timedelta(minutes=record.horizon_minutes)
        if due_at <= observation_time:
            due_count += 1
            journal.resolve(record.id, resolved_spot=observed_spot, resolved_at=observation_time)
            resolved_count += 1

    refreshed = journal.read_all()
    return ResolveResult(
        due_count=due_count,
        resolved_count=resolved_count,
        summary=summarize_records(refreshed),
    )
