from dataclasses import replace
from datetime import datetime, timedelta, timezone

from packages.gexy.horizon_metrics import summarize_by_horizon, wilson_lower_bound
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry, resolve_entry


def _resolved_entry(*, index: int, hit: bool, horizon: int = 1):
    created = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc) + timedelta(seconds=index)
    prediction = LivePrediction(
        direction="up",
        expected_move_points=1.0,
        primary_target=7801.0,
        invalidation_level=7795.0,
        confidence=0.95,
        horizon_minutes=horizon,
        regime="negative_gamma_acceleration",
    )
    entry = make_entry(created_at=created, spot=7800.0, prediction=prediction)
    realized_spot = 7801.0 if hit else 7799.0
    return resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized_spot)


def test_wilson_lower_bound_is_conservative_for_small_perfect_sample():
    assert wilson_lower_bound(30, 30) < 0.95


def test_perfect_large_sample_can_qualify_for_95_percent_promotion():
    entries = [_resolved_entry(index=i, hit=True) for i in range(100)]
    metrics = summarize_by_horizon(entries)[0]
    assert metrics.directional_accuracy == 1.0
    assert metrics.wilson_lower_bound >= 0.95
    assert metrics.qualified_for_promotion is True


def test_99_percent_raw_accuracy_is_not_automatically_95_percent_proven():
    entries = [_resolved_entry(index=i, hit=(i != 99)) for i in range(100)]
    metrics = summarize_by_horizon(entries)[0]
    assert metrics.directional_accuracy == 0.99
    assert metrics.wilson_lower_bound < 0.95
    assert metrics.qualified_for_promotion is False


def test_minimum_sample_gate_blocks_tiny_sample_even_with_relaxed_interval():
    entries = [_resolved_entry(index=i, hit=True) for i in range(5)]
    metrics = summarize_by_horizon(
        entries,
        target_directional_accuracy=0.50,
        minimum_resolved_for_promotion=30,
    )[0]
    assert metrics.wilson_lower_bound >= 0.50
    assert metrics.qualified_for_promotion is False
