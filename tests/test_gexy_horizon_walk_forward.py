from packages.gexy.horizon_walk_forward import (
    select_shortest_walk_forward_validated_horizon,
    validate_horizon_walk_forward,
)


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
