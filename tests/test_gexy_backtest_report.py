import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry, resolve_entry

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_backtest_report.py"
SPEC = importlib.util.spec_from_file_location("gexy_backtest_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _resolved_entry(*, created_minute: int, direction: str, realized_move: float, horizon: int = 5):
    created = datetime(2026, 8, 14, 16, created_minute, tzinfo=timezone.utc)
    expected = 2.0 if direction == "up" else -2.0
    prediction = LivePrediction(
        direction=direction,
        expected_move_points=expected,
        primary_target=6500.0 + expected,
        invalidation_level=6500.0,
        confidence=0.75,
        horizon_minutes=horizon,
        regime="test",
    )
    entry = make_entry(created_at=created, spot=6500.0, prediction=prediction, model_version="test")
    return resolve_entry(
        entry,
        resolved_at=created + timedelta(minutes=horizon),
        realized_spot=6500.0 + realized_move,
    )


def test_backtest_report_scores_frozen_predictions_and_baseline():
    rows = [
        _resolved_entry(created_minute=0, direction="down", realized_move=-1.0),
        _resolved_entry(created_minute=1, direction="up", realized_move=-1.0),
        _resolved_entry(created_minute=2, direction="down", realized_move=-2.0),
        _resolved_entry(created_minute=3, direction="down", realized_move=1.0),
        _resolved_entry(created_minute=4, direction="down", realized_move=-1.0),
    ]

    report = MODULE.build_report(rows, horizon_minutes=5, journal_label="test.jsonl")
    metrics = report["overall"]

    assert report["method"] == "frozen_prediction_journal_backtest"
    assert report["execution_enabled"] is False
    assert metrics["resolved"] == 5
    assert metrics["directional_accuracy"] == 0.6
    assert metrics["always_down_accuracy"] == 0.8
    assert metrics["lift_vs_best_constant"] == pytest.approx(-0.2)
    assert report["by_horizon"]["5"]["resolved"] == 5


def test_backtest_report_rejects_out_of_range_horizon():
    try:
        MODULE.build_report([], horizon_minutes=61)
    except ValueError as exc:
        assert "between 1 and 60" in str(exc)
    else:
        raise AssertionError("expected ValueError")
