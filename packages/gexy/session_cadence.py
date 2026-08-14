from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from statistics import mean, median
from typing import Iterable, Mapping


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


@dataclass(frozen=True)
class SchedulerExecutionReport:
    cycles_with_scheduler_metrics: int
    target_interval_seconds: float | None
    mean_cycle_seconds: float | None
    median_cycle_seconds: float | None
    p90_cycle_seconds: float | None
    max_cycle_seconds: float | None
    overrun_cycles: int
    overrun_cycle_fraction: float | None
    missed_intervals_total: int
    max_missed_intervals_single_cycle: int
    mean_start_lag_seconds: float | None
    p90_start_lag_seconds: float | None
    max_start_lag_seconds: float | None
    mean_sleep_seconds: float | None


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


def _as_nonnegative_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number >= 0.0 else None


def _as_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    return number if number >= 0 and float(value) == number else None


def summarize_scheduler_execution(
    payloads: Iterable[Mapping[str, object]],
) -> SchedulerExecutionReport:
    """Summarize anchored-scheduler health from collector log payloads.

    Old session logs legitimately contain no ``scheduler`` object. In that case
    all distribution metrics remain ``None`` and the cycle count is zero, which
    gives us a clean pre-fix baseline rather than pretending scheduler health was
    measured before instrumentation existed.
    """
    cycle_seconds: list[float] = []
    start_lags: list[float] = []
    sleeps: list[float] = []
    missed: list[int] = []
    target_intervals: list[float] = []
    overrun_cycles = 0

    for payload in payloads:
        scheduler = payload.get("scheduler")
        if not isinstance(scheduler, Mapping):
            continue

        target = _as_nonnegative_float(scheduler.get("target_interval_seconds"))
        cycle = _as_nonnegative_float(scheduler.get("cycle_elapsed_seconds"))
        start_lag = _as_nonnegative_float(scheduler.get("start_lag_seconds"))
        sleep_seconds = _as_nonnegative_float(scheduler.get("sleep_seconds"))
        missed_intervals = _as_nonnegative_int(scheduler.get("missed_intervals"))
        overrun = _as_nonnegative_float(scheduler.get("overrun_seconds"))

        # Require the core scheduler fields so partially malformed records cannot
        # distort operational conclusions.
        if target is None or cycle is None or start_lag is None or missed_intervals is None:
            continue

        target_intervals.append(target)
        cycle_seconds.append(cycle)
        start_lags.append(start_lag)
        missed.append(missed_intervals)
        if sleep_seconds is not None:
            sleeps.append(sleep_seconds)
        if overrun is not None and overrun > 0.0:
            overrun_cycles += 1

    count = len(cycle_seconds)
    if not count:
        return SchedulerExecutionReport(
            cycles_with_scheduler_metrics=0,
            target_interval_seconds=None,
            mean_cycle_seconds=None,
            median_cycle_seconds=None,
            p90_cycle_seconds=None,
            max_cycle_seconds=None,
            overrun_cycles=0,
            overrun_cycle_fraction=None,
            missed_intervals_total=0,
            max_missed_intervals_single_cycle=0,
            mean_start_lag_seconds=None,
            p90_start_lag_seconds=None,
            max_start_lag_seconds=None,
            mean_sleep_seconds=None,
        )

    # A session should use one target interval. If a log contains mixed values,
    # report the most recent configured target rather than averaging schedules.
    target_interval = target_intervals[-1]
    return SchedulerExecutionReport(
        cycles_with_scheduler_metrics=count,
        target_interval_seconds=target_interval,
        mean_cycle_seconds=mean(cycle_seconds),
        median_cycle_seconds=median(cycle_seconds),
        p90_cycle_seconds=_nearest_rank(cycle_seconds, 0.90),
        max_cycle_seconds=max(cycle_seconds),
        overrun_cycles=overrun_cycles,
        overrun_cycle_fraction=overrun_cycles / count,
        missed_intervals_total=sum(missed),
        max_missed_intervals_single_cycle=max(missed),
        mean_start_lag_seconds=mean(start_lags),
        p90_start_lag_seconds=_nearest_rank(start_lags, 0.90),
        max_start_lag_seconds=max(start_lags),
        mean_sleep_seconds=mean(sleeps) if sleeps else None,
    )
