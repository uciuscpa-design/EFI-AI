from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping

from .horizon_metrics import DEFAULT_WILSON_Z, wilson_lower_bound
from .prediction_journal import PredictionJournalEntry

DEFAULT_TARGET_DIRECTIONAL_ACCURACY = 0.95
DEFAULT_MIN_RESOLVED = 100
DEFAULT_MIN_SESSIONS = 3
DEFAULT_MIN_LIFT_VS_BASELINE = 0.05
DEFAULT_MIN_POSITIVE_LIFT_SESSION_FRACTION = 2.0 / 3.0


@dataclass(frozen=True)
class HorizonQualification:
    horizon_minutes: int
    sessions: int
    resolved: int
    directional_accuracy: float
    wilson_lower_bound: float
    baseline_accuracy: float
    lift_vs_baseline: float
    positive_lift_sessions: int
    positive_lift_session_fraction: float
    target_directional_accuracy: float
    minimum_resolved: int
    minimum_sessions: int
    minimum_lift_vs_baseline: float
    minimum_positive_lift_session_fraction: float
    qualified: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class QualificationReport:
    session_dates: tuple[str, ...]
    horizons: tuple[HorizonQualification, ...]
    qualified_horizons_minutes: tuple[int, ...]
    shortest_qualified_horizon_minutes: int | None
    automatic_promotion: bool
    status: str


def _realized_direction(entry: PredictionJournalEntry) -> str:
    move = entry.realized_move_points
    if move is None:
        return "flat"
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _baseline_accuracy(entries: Iterable[PredictionJournalEntry]) -> float:
    rows = list(entries)
    if not rows:
        return 0.0
    counts = {"up": 0, "down": 0}
    for entry in rows:
        direction = _realized_direction(entry)
        if direction in counts:
            counts[direction] += 1
    return max(counts.values()) / len(rows)


def qualify_horizons(
    session_entries: Mapping[str, Iterable[PredictionJournalEntry]],
    *,
    target_directional_accuracy: float = DEFAULT_TARGET_DIRECTIONAL_ACCURACY,
    minimum_resolved: int = DEFAULT_MIN_RESOLVED,
    minimum_sessions: int = DEFAULT_MIN_SESSIONS,
    minimum_lift_vs_baseline: float = DEFAULT_MIN_LIFT_VS_BASELINE,
    minimum_positive_lift_session_fraction: float = DEFAULT_MIN_POSITIVE_LIFT_SESSION_FRACTION,
    wilson_z: float = DEFAULT_WILSON_Z,
) -> QualificationReport:
    """Evaluate fine horizons conservatively across independent session snapshots.

    A horizon can qualify only if it has enough independent sessions, enough
    resolved observations, a Wilson lower bound at the target accuracy, positive
    lift over the best constant-direction baseline, and positive lift in a
    sufficient fraction of sessions. This remains shadow-only: automatic
    promotion is always disabled.
    """
    if not 0.0 < target_directional_accuracy <= 1.0:
        raise ValueError("target_directional_accuracy must be in (0, 1]")
    if minimum_resolved <= 0:
        raise ValueError("minimum_resolved must be positive")
    if minimum_sessions <= 0:
        raise ValueError("minimum_sessions must be positive")
    if minimum_lift_vs_baseline < 0.0:
        raise ValueError("minimum_lift_vs_baseline must be non-negative")
    if not 0.0 <= minimum_positive_lift_session_fraction <= 1.0:
        raise ValueError("minimum_positive_lift_session_fraction must be in [0, 1]")

    normalized: dict[str, list[PredictionJournalEntry]] = {}
    for session_date, entries in session_entries.items():
        rows = [entry for entry in entries if entry.resolved]
        if rows:
            normalized[str(session_date)] = rows

    grouped: dict[int, list[tuple[str, PredictionJournalEntry]]] = defaultdict(list)
    for session_date, rows in normalized.items():
        for entry in rows:
            grouped[entry.prediction.horizon_minutes].append((session_date, entry))

    metrics: list[HorizonQualification] = []
    for horizon in sorted(grouped):
        tagged_rows = grouped[horizon]
        rows = [entry for _, entry in tagged_rows]
        resolved = len(rows)
        hits = sum(1 for entry in rows if bool(entry.directional_hit))
        accuracy = hits / resolved
        lower_bound = wilson_lower_bound(hits, resolved, z=wilson_z)
        baseline = _baseline_accuracy(rows)
        lift = accuracy - baseline

        by_session: dict[str, list[PredictionJournalEntry]] = defaultdict(list)
        for session_date, entry in tagged_rows:
            by_session[session_date].append(entry)
        positive_lift_sessions = 0
        for session_rows in by_session.values():
            session_accuracy = sum(1 for entry in session_rows if bool(entry.directional_hit)) / len(session_rows)
            if session_accuracy - _baseline_accuracy(session_rows) > 0.0:
                positive_lift_sessions += 1
        sessions = len(by_session)
        positive_fraction = positive_lift_sessions / sessions if sessions else 0.0

        reasons: list[str] = []
        if sessions < minimum_sessions:
            reasons.append("insufficient_sessions")
        if resolved < minimum_resolved:
            reasons.append("insufficient_resolved")
        if lower_bound < target_directional_accuracy:
            reasons.append("wilson_below_target")
        if lift < minimum_lift_vs_baseline:
            reasons.append("insufficient_lift_vs_baseline")
        if positive_fraction < minimum_positive_lift_session_fraction:
            reasons.append("insufficient_cross_session_lift_stability")

        metrics.append(
            HorizonQualification(
                horizon_minutes=horizon,
                sessions=sessions,
                resolved=resolved,
                directional_accuracy=accuracy,
                wilson_lower_bound=lower_bound,
                baseline_accuracy=baseline,
                lift_vs_baseline=lift,
                positive_lift_sessions=positive_lift_sessions,
                positive_lift_session_fraction=positive_fraction,
                target_directional_accuracy=target_directional_accuracy,
                minimum_resolved=minimum_resolved,
                minimum_sessions=minimum_sessions,
                minimum_lift_vs_baseline=minimum_lift_vs_baseline,
                minimum_positive_lift_session_fraction=minimum_positive_lift_session_fraction,
                qualified=not reasons,
                reasons=tuple(reasons),
            )
        )

    qualified = tuple(row.horizon_minutes for row in metrics if row.qualified)
    session_dates = tuple(sorted(normalized))
    if len(session_dates) < minimum_sessions:
        status = "not_ready"
    elif qualified:
        status = "eligible_for_manual_review"
    else:
        status = "no_qualified_horizon"

    return QualificationReport(
        session_dates=session_dates,
        horizons=tuple(metrics),
        qualified_horizons_minutes=qualified,
        shortest_qualified_horizon_minutes=min(qualified) if qualified else None,
        automatic_promotion=False,
        status=status,
    )
