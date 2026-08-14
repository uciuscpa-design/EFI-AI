from datetime import datetime, timedelta, timezone

from packages.gexy.horizon_walk_forward import (
    outcomes_by_horizon_from_entries,
    select_shortest_walk_forward_validated_horizon,
    select_shortest_walk_forward_validated_horizon_from_entries,
    validate_horizon_walk_forward,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry, resolve_entry


def _resolved_entry(created_at: datetime, horizon: int, hit: bool):
    direction = "up"
    prediction = LivePrediction(
        direction=direction,
        expected_move_points=1.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.5,
        horizon_minutes=horizon,
        regime="positive_gamma_mean_reversion",
    )
    entry = make_entry(created_at=created_at, spot=100.0, prediction=prediction)
    realized_spot = 101.0 if hit else 99.0
    return resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized_spot)


def test_walk_forward_rejects_horizon_that_fails_unseen_block() -> None:
    outcomes = [True] * 300 + [True] * 69 + [False] * 31
    result = validate_horizon_walk_forward(
        outcomes,
        min_validation_samples=100,
        min_success_rate=0.70,
        validation_fraction=0.25,
    )

    assert result["train_samples"] == 300
    assert result["validation_samples"] == 100
    assert result["validation_success_rate"] == 0.69
    assert result["validated"] is False
    assert result["automatic_promotion"] is False


def test_selector_chooses_shortest_horizon_that_passes_unseen_block() -> None:
    one_minute = [True] * 300 + [True] * 69 + [False] * 31
    two_minute = [True] * 300 + [True] * 72 + [False] * 28
    three_minute = [True] * 300 + [True] * 80 + [False] * 20

    decision = select_shortest_walk_forward_validated_horizon(
        {1: one_minute, 2: two_minute, 3: three_minute},
        min_validation_samples=100,
        min_success_rate=0.70,
        validation_fraction=0.25,
    )

    assert decision["recommended"] is True
    assert decision["horizon_minutes"] == 2
    assert decision["validation_success_rate"] == 0.72
    assert decision["automatic_promotion"] is False


def test_journal_adapter_sorts_entries_and_groups_by_horizon() -> None:
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entries = [
        _resolved_entry(t0 + timedelta(minutes=3), 2, True),
        _resolved_entry(t0 + timedelta(minutes=1), 1, False),
        _resolved_entry(t0 + timedelta(minutes=2), 1, True),
        _resolved_entry(t0, 2, False),
    ]

    grouped = outcomes_by_horizon_from_entries(entries)
    assert grouped == {2: [False, True], 1: [False, True]}

    decision = select_shortest_walk_forward_validated_horizon_from_entries(
        entries,
        min_validation_samples=1,
        min_success_rate=1.0,
        validation_fraction=0.5,
    )
    assert decision["recommended"] is True
    assert decision["horizon_minutes"] == 1
    assert decision["automatic_promotion"] is False
