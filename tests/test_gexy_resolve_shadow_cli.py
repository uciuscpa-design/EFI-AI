import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, load_entries, make_entry


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_resolve_due.py"
SPEC = importlib.util.spec_from_file_location("gexy_resolve_due", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _prediction(horizon: int, direction: str = "up") -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=2.0 if direction == "up" else -2.0,
        primary_target=7802.0,
        invalidation_level=7790.0,
        confidence=0.8,
        horizon_minutes=horizon,
        regime="negative_gamma_acceleration",
    )


def test_shadow_and_production_due_sets_are_isolated(tmp_path):
    observed_at = datetime(2026, 8, 14, 14, 1, 30, tzinfo=timezone.utc)
    created_at = observed_at - timedelta(minutes=1, seconds=30)
    production_path = tmp_path / "production.jsonl"
    shadow_path = tmp_path / "shadow.jsonl"

    append_entry(
        production_path,
        make_entry(created_at=created_at, spot=7800.0, prediction=_prediction(1)),
    )
    append_entry(
        production_path,
        make_entry(created_at=created_at, spot=7800.0, prediction=_prediction(5)),
    )
    append_entry(
        shadow_path,
        make_entry(
            created_at=created_at,
            spot=7800.0,
            prediction=_prediction(1),
            model_version="gexy-shadow-fine-v1",
        ),
    )
    append_entry(
        shadow_path,
        make_entry(
            created_at=created_at,
            spot=7800.0,
            prediction=_prediction(2),
            model_version="gexy-shadow-fine-v1",
        ),
    )

    production_entries, production_due = MODULE._load_due(
        production_path,
        observed_at=observed_at,
        tolerance_seconds=90,
    )
    shadow_entries, shadow_due = MODULE._load_due(
        shadow_path,
        observed_at=observed_at,
        tolerance_seconds=90,
    )

    assert [entry.prediction.horizon_minutes for entry in production_due] == [1]
    assert [entry.prediction.horizon_minutes for entry in shadow_due] == [1]

    production_ids = MODULE._resolve_journal(
        production_path,
        production_entries,
        production_due,
        observed_at=observed_at,
        realized_spot=7803.0,
    )
    shadow_ids = MODULE._resolve_journal(
        shadow_path,
        shadow_entries,
        shadow_due,
        observed_at=observed_at,
        realized_spot=7803.0,
    )

    assert len(production_ids) == 1
    assert len(shadow_ids) == 1

    production_after = load_entries(production_path)
    shadow_after = load_entries(shadow_path)
    assert [entry.resolved for entry in production_after] == [True, False]
    assert [entry.resolved for entry in shadow_after] == [True, False]
    assert production_after[0].realized_spot == shadow_after[0].realized_spot == 7803.0
    assert shadow_after[0].model_version == "gexy-shadow-fine-v1"


def test_empty_due_set_does_not_rewrite_journal(tmp_path):
    path = tmp_path / "shadow.jsonl"
    created_at = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(
        created_at=created_at,
        spot=7800.0,
        prediction=_prediction(10),
        model_version="gexy-shadow-fine-v1",
    )
    append_entry(path, entry)
    before = path.read_text(encoding="utf-8")

    ids = MODULE._resolve_journal(
        path,
        [entry],
        [],
        observed_at=created_at + timedelta(minutes=1),
        realized_spot=7801.0,
    )

    assert ids == []
    assert path.read_text(encoding="utf-8") == before
