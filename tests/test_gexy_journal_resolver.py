from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.gexy.journal_resolver import resolve_due_predictions
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, load_entries, make_entry


def _prediction(direction: str, move: float, horizon: int = 30) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=move,
        primary_target=None,
        invalidation_level=None,
        confidence=0.6,
        horizon_minutes=horizon,
        regime="positive_gamma_mean_reversion",
    )


def test_resolver_only_resolves_due_pending_entries(tmp_path) -> None:
    path = tmp_path / "predictions.jsonl"
    t0 = datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc)
    append_entry(path, make_entry(created_at=t0, spot=7750, prediction=_prediction("up", 10)))
    append_entry(path, make_entry(created_at=t0 + timedelta(minutes=20), spot=7755, prediction=_prediction("down", -5)))

    result = resolve_due_predictions(
        path,
        observation_time=t0 + timedelta(minutes=35),
        observed_spot=7762,
    )

    assert result.due_count == 1
    assert result.resolved_count == 1
    entries = load_entries(path)
    assert entries[0].resolved is True
    assert entries[0].realized_move_points == 12
    assert entries[0].directional_hit is True
    assert entries[1].resolved is False
    assert result.summary.resolved == 1
    assert result.summary.pending == 1


def test_resolver_requires_timezone_aware_observation(tmp_path) -> None:
    path = tmp_path / "predictions.jsonl"
    try:
        resolve_due_predictions(path, observation_time=datetime(2026, 8, 13, 13, 0), observed_spot=7750)
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError")
