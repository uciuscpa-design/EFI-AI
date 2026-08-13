from datetime import datetime, timedelta, timezone

import pytest

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import (
    LIVE_MODEL_VERSION,
    append_entry,
    load_entries,
    make_entry,
    resolve_entry,
    rewrite_entries,
    summarize_entries,
)


def _prediction(direction: str = 'up', move: float = 5.0, confidence: float = 0.7) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=move,
        primary_target=7755.0,
        invalidation_level=7735.0,
        confidence=confidence,
        horizon_minutes=30,
        regime='positive_gamma_mean_reversion',
    )


def test_journal_round_trip_and_resolution(tmp_path) -> None:
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(created_at=created, spot=7750.0, prediction=_prediction())
    path = tmp_path / 'journal.jsonl'
    append_entry(path, entry)

    loaded = load_entries(path)
    assert loaded == [entry]
    assert loaded[0].due_at == created + timedelta(minutes=30)
    assert loaded[0].model_version == LIVE_MODEL_VERSION

    resolved = resolve_entry(
        loaded[0],
        resolved_at=created + timedelta(minutes=31),
        realized_spot=7754.0,
    )
    assert resolved.realized_move_points == 4.0
    assert resolved.directional_hit is True
    assert resolved.absolute_error_points == 1.0
    assert resolved.model_version == LIVE_MODEL_VERSION

    rewrite_entries(path, [resolved])
    reread = load_entries(path)
    assert reread[0].resolved is True
    assert reread[0].realized_spot == 7754.0


def test_model_version_is_recorded_and_part_of_prediction_id() -> None:
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(
        created_at=created,
        spot=7750.0,
        prediction=_prediction(),
        model_version='gexy-live-shadow-v2',
    )
    assert entry.model_version == 'gexy-live-shadow-v2'
    assert entry.prediction_id.endswith('gexy-live-shadow-v2')


def test_model_version_rejects_empty_value() -> None:
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match='model_version'):
        make_entry(created_at=created, spot=7750.0, prediction=_prediction(), model_version='  ')


def test_resolution_rejects_early_observation() -> None:
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(created_at=created, spot=7750.0, prediction=_prediction())
    with pytest.raises(ValueError, match='horizon has not elapsed'):
        resolve_entry(entry, resolved_at=created + timedelta(minutes=20), realized_spot=7751.0)


def test_summary_scores_only_resolved_entries() -> None:
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    first = resolve_entry(
        make_entry(created_at=created, spot=7750.0, prediction=_prediction('up', 5.0, 0.8)),
        resolved_at=created + timedelta(minutes=30),
        realized_spot=7754.0,
    )
    second = resolve_entry(
        make_entry(created_at=created + timedelta(minutes=1), spot=7750.0, prediction=_prediction('down', -5.0, 0.6)),
        resolved_at=created + timedelta(minutes=31),
        realized_spot=7752.0,
    )
    pending = make_entry(created_at=created + timedelta(minutes=2), spot=7750.0, prediction=_prediction())

    summary = summarize_entries([first, second, pending])
    assert summary.total == 3
    assert summary.resolved == 2
    assert summary.pending == 1
    assert summary.directional_accuracy == 0.5
    assert summary.mean_absolute_error_points == 4.0
    assert summary.mean_confidence == pytest.approx(0.7)
