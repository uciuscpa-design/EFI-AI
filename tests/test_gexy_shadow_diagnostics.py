import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import PredictionJournalEntry, rewrite_entries

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_shadow_diagnostics.py"
SPEC = importlib.util.spec_from_file_location("gexy_shadow_diagnostics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _entry(*, horizon: int, direction: str, move: float, hit: bool, confidence: float = 0.95):
    created = datetime(2026, 8, 14, 14, 30, tzinfo=timezone.utc)
    prediction = LivePrediction(
        direction=direction,
        expected_move_points=5.0 if direction == "up" else -5.0,
        primary_target=None,
        invalidation_level=None,
        confidence=confidence,
        horizon_minutes=horizon,
        regime="test_regime",
    )
    return PredictionJournalEntry(
        prediction_id=f"{horizon}-{direction}-{move}",
        created_at=created,
        spot=6500.0,
        prediction=prediction,
        model_version="gexy-shadow-fine-v1",
        resolved_at=created + timedelta(minutes=horizon),
        realized_spot=6500.0 + move,
        realized_move_points=move,
        directional_hit=hit,
        absolute_error_points=abs(prediction.expected_move_points - move),
    )


def test_build_diagnostics_identifies_raw_and_inverted_behavior(tmp_path):
    path = tmp_path / "shadow.jsonl"
    rows = []
    for i in range(30):
        rows.append(_entry(horizon=1, direction="up", move=-1.0, hit=False))
        rows.append(_entry(horizon=20, direction="up", move=1.0, hit=True))
    rewrite_entries(path, rows)

    report = MODULE.build_diagnostics(path)

    assert report["resolved_entries"] == 60
    assert report["by_horizon"]["1"]["directional_accuracy"] == 0.0
    assert report["by_horizon"]["1"]["inverted_directional_accuracy"] == 1.0
    assert report["best_raw_horizon_min_30"]["horizon_minutes"] == 20
    assert report["best_inverted_horizon_min_30"]["horizon_minutes"] == 1


def test_build_diagnostics_reports_confidence_variation(tmp_path):
    path = tmp_path / "shadow.jsonl"
    rewrite_entries(
        path,
        [
            _entry(horizon=1, direction="up", move=1.0, hit=True, confidence=0.6),
            _entry(horizon=1, direction="up", move=-1.0, hit=False, confidence=0.9),
        ],
    )

    report = MODULE.build_diagnostics(path)

    assert report["confidence"]["min"] == 0.6
    assert report["confidence"]["max"] == 0.9
    assert report["confidence"]["unique_rounded_4dp"] == [0.6, 0.9]
