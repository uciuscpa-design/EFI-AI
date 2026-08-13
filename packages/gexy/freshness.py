from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FreshnessResult:
    fresh: bool
    age_seconds: float
    max_age_seconds: float
    reason: str


def validate_snapshot_freshness(
    *,
    observation_time: datetime,
    quote_time: datetime,
    max_age_seconds: float = 90.0,
) -> FreshnessResult:
    """Reject stale/future quotes before they can enter the live prediction path."""
    if max_age_seconds <= 0:
        raise ValueError("max_age_seconds must be positive")
    if observation_time.tzinfo is None or quote_time.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")

    age = (observation_time - quote_time).total_seconds()
    if age < 0:
        return FreshnessResult(False, age, max_age_seconds, "quote timestamp is in the future")
    if age > max_age_seconds:
        return FreshnessResult(False, age, max_age_seconds, "quote is stale")
    return FreshnessResult(True, age, max_age_seconds, "fresh")
