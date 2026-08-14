from datetime import datetime, timedelta, timezone

from packages.gexy.due_resolution import due_now
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry


def _entry(created_at: datetime, horizon: int = 5):
    prediction = LivePrediction(
        direction="up",
        expected_move_points=2.0,
        primary_target=7802.0,
        invalidation_level=None,
        confidence=0.6,
        horizon_minutes=horizon,
        regime="test",
    )
    return make_entry(created_at=created_at, spot=7800.0, prediction=prediction)


def test_due_now_accepts_entry_within_tolerance():
    created = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
    entry = _entry(created)
    observed = entry.due_at + timedelta(seconds=45)
    assert due_now([entry], observed_at=observed, tolerance_seconds=90) == [entry]


def test_due_now_rejects_late_entry():
    created = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
    entry = _entry(created)
    observed = entry.due_at + timedelta(seconds=91)
    assert due_now([entry], observed_at=observed, tolerance_seconds=90) == []


def test_due_now_rejects_not_yet_due_entry():
    created = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
    entry = _entry(created)
    observed = entry.due_at - timedelta(seconds=1)
    assert due_now([entry], observed_at=observed, tolerance_seconds=90) == []
