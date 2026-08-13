from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .prediction_journal import (
    JournalSummary,
    load_entries,
    resolve_entry,
    rewrite_entries,
    summarize_entries,
)


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
    """Resolve pending predictions whose forecast horizon has elapsed.

    One observation may resolve multiple due entries. Future entries and entries
    that are already resolved are preserved unchanged. The observation timestamp
    must be timezone-aware so horizon comparisons remain unambiguous.
    """
    if observation_time.tzinfo is None:
        raise ValueError("observation_time must be timezone-aware")
    if observed_spot <= 0:
        raise ValueError("observed_spot must be positive")

    observation_time = observation_time.astimezone(timezone.utc)
    entries = load_entries(journal_path)
    updated = []
    due_count = 0
    resolved_count = 0

    for entry in entries:
        if entry.resolved or entry.due_at > observation_time:
            updated.append(entry)
            continue
        due_count += 1
        updated.append(
            resolve_entry(
                entry,
                resolved_at=observation_time,
                realized_spot=observed_spot,
            )
        )
        resolved_count += 1

    if resolved_count:
        rewrite_entries(journal_path, updated)

    return ResolveResult(
        due_count=due_count,
        resolved_count=resolved_count,
        summary=summarize_entries(updated),
    )
