from __future__ import annotations

from collections.abc import Iterable

from .prediction_journal import PredictionJournalEntry


def validate_horizon_walk_forward(
    outcomes: Iterable[bool],
    *,
    min_validation_samples: int = 100,
    min_success_rate: float = 0.70,
    validation_fraction: float = 0.25,
) -> dict[str, object]:
    """Validate a horizon on the latest unseen chronological block.

    Outcomes must be supplied oldest-to-newest. The latest validation block is
    never used to establish the earlier training history. This helper is
    advisory only and does not promote or change production horizons.
    """
    if min_validation_samples <= 0:
        raise ValueError("min_validation_samples must be positive")
    if not 0.0 <= min_success_rate <= 1.0:
        raise ValueError("min_success_rate must be between 0 and 1")
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")

    ordered = [bool(value) for value in outcomes]
    if len(ordered) < 2:
        validation_size = 0
    else:
        validation_size = max(1, int(len(ordered) * validation_fraction))
        validation_size = min(validation_size, len(ordered) - 1)

    train_size = len(ordered) - validation_size
    validation = ordered[train_size:] if validation_size else []
    validation_success_rate = (
        sum(validation) / validation_size if validation_size else 0.0
    )
    validated = (
        train_size > 0
        and validation_size >= min_validation_samples
        and validation_success_rate >= min_success_rate
    )

    return {
        "validated": validated,
        "reason": (
            "unseen_block_clears_trust_gate"
            if validated
            else "unseen_block_does_not_clear_trust_gate"
        ),
        "total_samples": len(ordered),
        "train_samples": train_size,
        "validation_samples": validation_size,
        "validation_success_rate": validation_success_rate,
        "min_validation_samples": min_validation_samples,
        "min_success_rate": min_success_rate,
        "validation_fraction": validation_fraction,
        "automatic_promotion": False,
    }


def select_shortest_walk_forward_validated_horizon(
    outcomes_by_horizon: dict[int, Iterable[bool]],
    *,
    min_validation_samples: int = 100,
    min_success_rate: float = 0.70,
    validation_fraction: float = 0.25,
) -> dict[str, object]:
    """Return the shortest horizon whose unseen block clears the trust gate."""
    evaluated: dict[str, dict[str, object]] = {}
    passing: list[int] = []

    for horizon in sorted(outcomes_by_horizon):
        if horizon <= 0:
            continue
        result = validate_horizon_walk_forward(
            outcomes_by_horizon[horizon],
            min_validation_samples=min_validation_samples,
            min_success_rate=min_success_rate,
            validation_fraction=validation_fraction,
        )
        evaluated[str(horizon)] = result
        if result["validated"]:
            passing.append(horizon)

    if not passing:
        return {
            "recommended": False,
            "reason": "no_horizon_clears_walk_forward_gate",
            "evaluated": evaluated,
            "automatic_promotion": False,
        }

    horizon = min(passing)
    return {
        "recommended": True,
        "reason": "shortest_horizon_clears_walk_forward_gate",
        "horizon_minutes": horizon,
        "validation_success_rate": evaluated[str(horizon)]["validation_success_rate"],
        "evaluated": evaluated,
        "automatic_promotion": False,
    }


def outcomes_by_horizon_from_entries(
    entries: Iterable[PredictionJournalEntry],
) -> dict[int, list[bool]]:
    """Build chronological directional hit/miss sequences from resolved journal entries."""
    resolved = sorted(
        (
            entry
            for entry in entries
            if entry.resolved and entry.directional_hit is not None
        ),
        key=lambda entry: entry.created_at,
    )
    grouped: dict[int, list[bool]] = {}
    for entry in resolved:
        horizon = int(entry.prediction.horizon_minutes)
        grouped.setdefault(horizon, []).append(bool(entry.directional_hit))
    return grouped


def select_shortest_walk_forward_validated_horizon_from_entries(
    entries: Iterable[PredictionJournalEntry],
    *,
    min_validation_samples: int = 100,
    min_success_rate: float = 0.70,
    validation_fraction: float = 0.25,
) -> dict[str, object]:
    """Run the advisory shortest-horizon walk-forward gate on real journal entries."""
    return select_shortest_walk_forward_validated_horizon(
        outcomes_by_horizon_from_entries(entries),
        min_validation_samples=min_validation_samples,
        min_success_rate=min_success_rate,
        validation_fraction=validation_fraction,
    )
