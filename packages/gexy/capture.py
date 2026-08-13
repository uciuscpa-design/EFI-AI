from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from .freshness import FreshnessResult, validate_snapshot_freshness
from .recording import JsonlRecorder
from .snapshot_bridge import record_feature_state


@dataclass(frozen=True)
class CaptureResult:
    recorded: bool
    data_quality: str
    freshness: tuple[FreshnessResult, ...]


def capture_feature_state(
    recorder: JsonlRecorder,
    *,
    observation_time: datetime,
    spot: float,
    feature_state: Any,
    option_quote_times: Iterable[datetime],
    source: str = "alpaca",
    max_quote_age_seconds: float = 90.0,
) -> CaptureResult:
    """Record a live feature state only when all supplied option quotes are fresh.

    An empty quote set is rejected: a live signal must never be produced from a
    surface with no synchronized option observations.
    """
    quote_times = tuple(option_quote_times)
    if not quote_times:
        return CaptureResult(False, "insufficient_data", ())

    checks = tuple(
        validate_snapshot_freshness(
            observation_time=observation_time,
            quote_time=quote_time,
            max_age_seconds=max_quote_age_seconds,
        )
        for quote_time in quote_times
    )
    if not all(check.fresh for check in checks):
        return CaptureResult(False, "stale", checks)

    record_feature_state(
        recorder,
        timestamp=observation_time,
        spot=spot,
        feature_state=feature_state,
        source=source,
    )
    return CaptureResult(True, "live", checks)
