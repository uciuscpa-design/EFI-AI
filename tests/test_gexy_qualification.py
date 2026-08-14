from datetime import datetime, timedelta, timezone

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import PredictionJournalEntry
from packages.gexy.qualification import qualify_horizons

BASE_TIME = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)


def _entry(
    index: int,
    *,
    horizon: int,
    predicted: str,
    realized: str,
    resolved: bool = True,
) -> PredictionJournalEntry:
    created = BASE_TIME + timedelta(seconds=index)
    realized_move = 1.0 if realized == "up" else -1.0 if realized == "down" else 0.0
    prediction = LivePrediction(
        direction=predicted,
        expected_move_points=1.0 if predicted == "up" else -1.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.95,
        horizon_minutes=horizon,
        regime="test",
    )
    return PredictionJournalEntry(
        prediction_id=f"{index}-{horizon}-{predicted}-{realized}-{resolved}",
        created_at=created,
        spot=5000.0,
        prediction=prediction,
        model_version="test",
        resolved_at=created + timedelta(minutes=horizon) if resolved else None,
        realized_spot=5000.0 + realized_move if resolved else None,
        realized_move_points=realized_move if resolved else None,
        directional_hit=(predicted == realized) if resolved else None,
        absolute_error_points=(0.0 if predicted == realized else 2.0) if resolved else None,
    )


def _perfect_balanced_session(*, horizon: int, count: int, offset: int = 0):
    rows = []
    for index in range(count):
        direction = "up" if index % 2 == 0 else "down"
        rows.append(_entry(offset + index, horizon=horizon, predicted=direction, realized=direction))
    return rows


def test_one_session_never_qualifies_even_with_perfect_accuracy():
    report = qualify_horizons({"2026-08-10": _perfect_balanced_session(horizon=5, count=200)})

    metric = report.horizons[0]
    assert metric.total == 200
    assert metric.resolved == 200
    assert metric.unresolved == 0
    assert metric.resolution_coverage == 1.0
    assert metric.directional_accuracy == 1.0
    assert metric.lift_vs_baseline == 0.5
    assert metric.qualified is False
    assert "insufficient_sessions" in metric.reasons
    assert report.status == "not_ready"
    assert report.shortest_qualified_horizon_minutes is None
    assert report.automatic_promotion is False


def test_high_raw_accuracy_with_zero_baseline_lift_does_not_qualify():
    sessions = {}
    for session_index in range(3):
        rows = [
            _entry(session_index * 200 + index, horizon=10, predicted="down", realized="down")
            for index in range(200)
        ]
        sessions[f"2026-08-{10 + session_index:02d}"] = rows

    metric = qualify_horizons(sessions).horizons[0]

    assert metric.directional_accuracy == 1.0
    assert metric.baseline_accuracy == 1.0
    assert metric.lift_vs_baseline == 0.0
    assert metric.qualified is False
    assert "insufficient_lift_vs_baseline" in metric.reasons
    assert "insufficient_cross_session_lift_stability" in metric.reasons


def test_positive_lift_with_too_few_resolved_does_not_qualify():
    sessions = {
        "2026-08-10": _perfect_balanced_session(horizon=15, count=10, offset=0),
        "2026-08-11": _perfect_balanced_session(horizon=15, count=10, offset=100),
        "2026-08-12": _perfect_balanced_session(horizon=15, count=10, offset=200),
    }

    metric = qualify_horizons(sessions).horizons[0]

    assert metric.lift_vs_baseline == 0.5
    assert metric.qualified is False
    assert "insufficient_resolved" in metric.reasons


def test_low_resolution_coverage_rejects_otherwise_strong_horizon():
    sessions = {}
    for session_index, session_date in enumerate(("2026-08-10", "2026-08-11", "2026-08-12")):
        rows = []
        offset = session_index * 1000
        # 100 perfectly resolved balanced observations plus 100 missed due windows.
        rows.extend(_perfect_balanced_session(horizon=18, count=100, offset=offset))
        for index in range(100):
            direction = "up" if index % 2 == 0 else "down"
            rows.append(
                _entry(
                    offset + 500 + index,
                    horizon=18,
                    predicted=direction,
                    realized=direction,
                    resolved=False,
                )
            )
        sessions[session_date] = rows

    metric = qualify_horizons(sessions).horizons[0]

    assert metric.total == 600
    assert metric.resolved == 300
    assert metric.unresolved == 300
    assert metric.resolution_coverage == 0.5
    assert metric.directional_accuracy == 1.0
    assert metric.wilson_lower_bound >= 0.95
    assert metric.lift_vs_baseline == 0.5
    assert metric.qualified is False
    assert "insufficient_resolution_coverage" in metric.reasons


def test_sufficient_cross_session_accuracy_lift_coverage_and_evidence_can_qualify():
    sessions = {
        "2026-08-10": _perfect_balanced_session(horizon=20, count=200, offset=0),
        "2026-08-11": _perfect_balanced_session(horizon=20, count=200, offset=1000),
        "2026-08-12": _perfect_balanced_session(horizon=20, count=200, offset=2000),
    }

    report = qualify_horizons(sessions)
    metric = report.horizons[0]

    assert metric.total == 600
    assert metric.resolved == 600
    assert metric.resolution_coverage == 1.0
    assert metric.directional_accuracy == 1.0
    assert metric.wilson_lower_bound >= 0.95
    assert metric.lift_vs_baseline == 0.5
    assert metric.positive_lift_session_fraction == 1.0
    assert metric.qualified is True
    assert report.status == "eligible_for_manual_review"
    assert report.qualified_horizons_minutes == (20,)
    assert report.shortest_qualified_horizon_minutes == 20
    assert report.automatic_promotion is False


def test_shortest_qualified_horizon_is_selected():
    sessions = {}
    for session_index, session_date in enumerate(("2026-08-10", "2026-08-11", "2026-08-12")):
        rows = []
        rows.extend(_perfect_balanced_session(horizon=5, count=150, offset=session_index * 10000))
        rows.extend(_perfect_balanced_session(horizon=2, count=150, offset=session_index * 10000 + 5000))
        sessions[session_date] = rows

    report = qualify_horizons(sessions)

    assert report.qualified_horizons_minutes == (2, 5)
    assert report.shortest_qualified_horizon_minutes == 2
