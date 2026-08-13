from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, Protocol

from .capture import CaptureResult, capture_feature_state
from .recording import JsonlRecorder


@dataclass(frozen=True)
class SampleInput:
    observation_time: datetime
    spot: float
    feature_state: object
    option_quote_times: tuple[datetime, ...]


@dataclass(frozen=True)
class SampleEvent:
    scheduled_time: datetime
    result: CaptureResult


class SnapshotProvider(Protocol):
    def __call__(self, scheduled_time: datetime) -> SampleInput:
        ...


def sampling_schedule(
    *,
    start: datetime,
    end: datetime,
    interval_seconds: int = 60,
) -> tuple[datetime, ...]:
    """Return an inclusive deterministic sampling schedule."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    if end < start:
        raise ValueError("end must be >= start")
    step = timedelta(seconds=interval_seconds)
    times: list[datetime] = []
    current = start
    while current <= end:
        times.append(current)
        current += step
    return tuple(times)


def run_sampler(
    recorder: JsonlRecorder,
    *,
    schedule: Iterable[datetime],
    provider: SnapshotProvider,
    source: str = "alpaca",
    max_quote_age_seconds: float = 90.0,
) -> tuple[SampleEvent, ...]:
    """Execute a supplied schedule without sleeping or inventing timestamps.

    Timing belongs to the process runner/scheduler. This function is deliberately
    deterministic so historical replay and live capture use the same orchestration.
    """
    events: list[SampleEvent] = []
    for scheduled_time in schedule:
        sample = provider(scheduled_time)
        if sample.observation_time < scheduled_time:
            # Providers may observe slightly after the requested tick, but they
            # must never supply a pre-scheduled snapshot as though it were fresh.
            result = CaptureResult(False, "pre_schedule", ())
        else:
            result = capture_feature_state(
                recorder,
                observation_time=sample.observation_time,
                spot=sample.spot,
                feature_state=sample.feature_state,
                option_quote_times=sample.option_quote_times,
                source=source,
                max_quote_age_seconds=max_quote_age_seconds,
            )
        events.append(SampleEvent(scheduled_time, result))
    return tuple(events)
