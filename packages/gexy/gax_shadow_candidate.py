from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .gax_shadow_journal import GAXShadowRecord, index_gax_shadows
from .prediction_journal import PredictionJournalEntry


@dataclass(frozen=True)
class ShadowCandidateMetrics:
    resolved: int
    overrides: int
    production_accuracy: float
    candidate_accuracy: float
    lift: float


def _realized_direction(entry: PredictionJournalEntry) -> str:
    move = float(entry.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _candidate_direction(
    entry: PredictionJournalEntry,
    shadow: GAXShadowRecord,
    *,
    min_gax_magnitude: float,
) -> str:
    production = entry.prediction.direction
    gax = shadow.features.acceleration_bias
    if gax == "neutral" or shadow.features.magnitude < min_gax_magnitude:
        return production
    if gax == production:
        return production
    return gax


def score_shadow_candidate(
    entries: Iterable[PredictionJournalEntry],
    shadows: Iterable[GAXShadowRecord],
    *,
    min_gax_magnitude: float = 0.0,
) -> ShadowCandidateMetrics:
    if min_gax_magnitude < 0:
        raise ValueError("min_gax_magnitude must be non-negative")

    shadow_index = index_gax_shadows(shadows)
    paired = [
        (entry, shadow_index[entry.prediction_id])
        for entry in entries
        if entry.resolved and entry.prediction_id in shadow_index
    ]
    if not paired:
        return ShadowCandidateMetrics(0, 0, 0.0, 0.0, 0.0)

    production_hits = 0
    candidate_hits = 0
    overrides = 0
    for entry, shadow in paired:
        realized = _realized_direction(entry)
        production = entry.prediction.direction
        candidate = _candidate_direction(
            entry,
            shadow,
            min_gax_magnitude=min_gax_magnitude,
        )
        production_hits += production == realized
        candidate_hits += candidate == realized
        overrides += candidate != production

    resolved = len(paired)
    production_accuracy = production_hits / resolved
    candidate_accuracy = candidate_hits / resolved
    return ShadowCandidateMetrics(
        resolved=resolved,
        overrides=overrides,
        production_accuracy=production_accuracy,
        candidate_accuracy=candidate_accuracy,
        lift=candidate_accuracy - production_accuracy,
    )
