from __future__ import annotations

from datetime import datetime, timezone

from packages.gexy.journal_report import build_journal_report
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry, rewrite_entries


def _prediction(regime: str = "positive_gamma_mean_reversion") -> LivePrediction:
    return LivePrediction(
        direction="up",
        expected_move_points=5.0,
        primary_target=7755.0,
        invalidation_level=7735.0,
        confidence=0.6,
        horizon_minutes=30,
        regime=regime,
    )


def test_report_handles_empty_journal(tmp_path) -> None:
    report = build_journal_report(tmp_path / "missing.jsonl")
    assert report["summary"]["total"] == 0
    assert report["next_due_at"] is None


def test_report_summarizes_pending_and_resolved(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    first = make_entry(created_at=t0, spot=7750.0, prediction=_prediction())
    second = make_entry(created_at=t0.replace(minute=5), spot=7751.0, prediction=_prediction("negative_gamma_acceleration"))
    append_entry(path, first)
    append_entry(path, second)
    resolved_first = resolve_entry(first, resolved_at=t0.replace(minute=31), realized_spot=7757.0)
    rewrite_entries(path, [resolved_first, second])

    report = build_journal_report(path)
    assert report["summary"]["total"] == 2
    assert report["summary"]["resolved"] == 1
    assert report["summary"]["pending"] == 1
    assert report["summary"]["directional_accuracy"] == 1.0
    assert report["next_due_at"] == second.due_at.isoformat()
    assert set(report["by_regime"]) == {"negative_gamma_acceleration", "positive_gamma_mean_reversion"}
