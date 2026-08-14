from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from .prediction_journal import PredictionJournalEntry


DEFAULT_TARGET_DIRECTIONAL_ACCURACY = 0.95
DEFAULT_MIN_RESOLVED_FOR_PROMOTION = 30
DEFAULT_WILSON_Z = 1.959963984540054  # two-sided 95% interval


@dataclass(frozen=True)
class HorizonMetrics:
    horizon_minutes: int
    resolved: int
    directional_accuracy: float
    mean_absolute_error_points: float
    mean_confidence: float
    calibration_gap: float
    wilson_lower_bound: float
    target_directional_accuracy: float
    minimum_resolved_for_promotion: int
    qualified_for_promotion: bool


def wilson_lower_bound(successes: int, total: int, *, z: float = DEFAULT_WILSON_Z) -> float:
    """Return the Wilson-score lower confidence bound for a Bernoulli hit rate."""
    if total < 0:
        raise ValueError("total must be non-negative")
    if successes < 0 or successes > total:
        raise ValueError("successes must be between zero and total")
    if z <= 0:
        raise ValueError("z must be positive")
    if total == 0:
        return 0.0

    p_hat = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = p_hat + z2 / (2.0 * total)
    margin = z * sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * total)) / total)
    return max(0.0, (center - margin) / denominator)


def summarize_by_horizon(
    entries: Iterable[PredictionJournalEntry],
    *,
    target_directional_accuracy: float = DEFAULT_TARGET_DIRECTIONAL_ACCURACY,
    minimum_resolved_for_promotion: int = DEFAULT_MIN_RESOLVED_FOR_PROMOTION,
    wilson_z: float = DEFAULT_WILSON_Z,
) -> tuple[HorizonMetrics, ...]:
    if not 0.0 < target_directional_accuracy <= 1.0:
        raise ValueError("target_directional_accuracy must be in (0, 1]")
    if minimum_resolved_for_promotion <= 0:
        raise ValueError("minimum_resolved_for_promotion must be positive")

    grouped: dict[int, list[PredictionJournalEntry]] = defaultdict(list)
    for entry in entries:
        if not entry.resolved:
            continue
        grouped[entry.prediction.horizon_minutes].append(entry)

    output: list[HorizonMetrics] = []
    for horizon in sorted(grouped):
        rows = grouped[horizon]
        count = len(rows)
        hits = sum(1 for row in rows if row.directional_hit)
        accuracy = hits / count
        mae = sum(float(row.absolute_error_points or 0.0) for row in rows) / count
        confidence = sum(row.prediction.confidence for row in rows) / count
        lower_bound = wilson_lower_bound(hits, count, z=wilson_z)
        output.append(
            HorizonMetrics(
                horizon_minutes=horizon,
                resolved=count,
                directional_accuracy=accuracy,
                mean_absolute_error_points=mae,
                mean_confidence=confidence,
                calibration_gap=confidence - accuracy,
                wilson_lower_bound=lower_bound,
                target_directional_accuracy=target_directional_accuracy,
                minimum_resolved_for_promotion=minimum_resolved_for_promotion,
                qualified_for_promotion=(
                    count >= minimum_resolved_for_promotion
                    and lower_bound >= target_directional_accuracy
                ),
            )
        )
    return tuple(output)
