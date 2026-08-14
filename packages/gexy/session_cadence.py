from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from statistics import mean, median
from typing import Iterable


@dataclass(frozen=True)
class CadenceGap:
    start: str
    end: str
    seconds: float


@dataclass(frozen=True)
class CadenceReport:
    observations: int
    intervals: int
    target_interval_seconds: float
    mean_interval_seconds: float | None
    median_interval_seconds: float | None
    p90_interval_seconds: float | None
    max_interval_seconds: float | None
    intervals_over_90_seconds: int
    intervals_over_180_seconds: int
    intervals_within_target_plus_30_seconds: int
    target_plus_30_coverage: float | None
    largest_gaps: tuple[CadenceGap, ...]


def _nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def summarize_cadence(
    observed_times: Iterable[datetime],
    *,
    target_interval_seconds: float = 60.0,
    largest_gap_count: int = 10,
) -> CadenceReport:
    if target_interval_seconds <= 0:
        raise ValueError("target_interval_seconds must be positive")
    if largest_gap_count < 0:
        raise ValueError("largest_gap_count must be non-negative")

    times = sorted(set(observed_times))
    for timestamp in times:
        if timestamp.tzinfo is None:
            raise ValueError("observed timestamps must be timezone-aware")

    intervals: list[tuple[datetime, datetime, float]] = []
    for previous, current in zip(times, times[1:]):
        seconds = (current - previous).total_seconds()
        if seconds >= 0:
            intervals.append((previous, current, seconds))

    seconds_values = [row[2] for row in intervals]
    within_limit = target_interval_seconds + 30.0
    within_count = sum(1 for seconds in seconds_values if seconds <= within_limit)
    largest = sorted(intervals, key=lambda row: row[2], reverse=True)[:largest_gap_count]

    return CadenceReport(
        observations=len(times),
        intervals=len(seconds_values),
        target_interval_seconds=target_interval_seconds,
        mean_interval_seconds=mean(seconds_values) if seconds_values else None,
        median_interval_seconds=median(seconds_values) if seconds_values else None,
        p90_interval_seconds=_nearest_rank(seconds_values, 0.90),
        max_interval_seconds=max(seconds_values) if seconds_values else None,
        intervals_over_90_seconds=sum(1 for seconds in seconds_values if seconds > 90.0),
        intervals_over_180_seconds=sum(1 for seconds in seconds_values if seconds > 180.0),
        intervals_within_target_plus_30_seconds=within_count,
        target_plus_30_coverage=(within_count / len(seconds_values)) if seconds_values else None,
        largest_gaps=tuple(
            CadenceGap(start=start.isoformat(), end=end.isoformat(), seconds=seconds)
            for start, end, seconds in largest
        ),
    )
