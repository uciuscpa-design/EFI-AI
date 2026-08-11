from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from .calibration import ForecastLabel, make_label


@dataclass(frozen=True)
class MarketSnapshot:
    timestamp: datetime
    spot: float


@dataclass(frozen=True)
class ReplaySample:
    snapshot: MarketSnapshot
    label: ForecastLabel


def build_forward_labels(
    snapshots: Iterable[MarketSnapshot],
    *,
    horizon_minutes: int,
) -> list[ReplaySample]:
    """Create point-in-time forward labels using only later prices as outcomes.

    Snapshots are sorted chronologically. A target must be at least the requested
    horizon after the source timestamp. The first eligible target is used, making
    the behavior deterministic for irregularly sampled source data.
    """
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")
    ordered = sorted(snapshots, key=lambda item: item.timestamp)
    horizon = timedelta(minutes=horizon_minutes)
    results: list[ReplaySample] = []
    for i, source in enumerate(ordered):
        target = next((candidate for candidate in ordered[i + 1:] if candidate.timestamp >= source.timestamp + horizon), None)
        if target is None:
            continue
        results.append(
            ReplaySample(
                snapshot=source,
                label=make_label(source.spot, target.spot, horizon_minutes),
            )
        )
    return results
