from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable

from .prediction_journal import JournalEntry


@dataclass(frozen=True)
class HorizonMetrics:
    horizon_minutes: int
    resolved: int
    directional_accuracy: float
    mean_absolute_error_points: float
    mean_confidence: float
    calibration_gap: float


def summarize_by_horizon(entries: Iterable[JournalEntry]) -> tuple[HorizonMetrics, ...]:
    grouped: dict[int, list[JournalEntry]] = defaultdict(list)
    for entry in entries:
        if not entry.resolved:
            continue
        grouped[entry.horizon_minutes].append(entry)

    output: list[HorizonMetrics] = []
    for horizon in sorted(grouped):
        rows = grouped[horizon]
        count = len(rows)
        accuracy = sum(1.0 for row in rows if row.directional_hit) / count
        mae = sum(float(row.absolute_error_points or 0.0) for row in rows) / count
        confidence = sum(row.confidence for row in rows) / count
        output.append(
            HorizonMetrics(
                horizon_minutes=horizon,
                resolved=count,
                directional_accuracy=accuracy,
                mean_absolute_error_points=mae,
                mean_confidence=confidence,
                calibration_gap=confidence - accuracy,
            )
        )
    return tuple(output)
