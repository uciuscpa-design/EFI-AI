from datetime import datetime, timedelta, timezone

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry, rewrite_entries, resolve_entry
from scripts.gexy_shadow_report import build_shadow_report


def _prediction(horizon: int) -> LivePrediction:
    return LivePrediction(
        direction="up",
        expected_move_points=1.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.9,
        horizon_minutes=horizon,
        regime="test",
    )


def _resolved_entry(horizon: int, idx: int, hit: bool):
    created = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc) + timedelta(seconds=idx)
    entry = make_entry(
        created_at=created,
        spot=100.0,
        prediction=_prediction(horizon),
        model_version="gexy-shadow-fine-v1",
    )
    realized = 101.0 if hit else 99.0
    return resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized)


def test_shadow_report_selects_shortest_qualified_horizon(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    rows = []
    rows.extend(_resolved_entry(1, i, True) for i in range(200))
    rows.extend(_resolved_entry(2, 1000 + i, True) for i in range(200))
    rows.extend(_resolved_entry(3, 2000 + i, i < 150) for i in range(200))
    rewrite_entries(journal, rows)

    report = build_shadow_report(journal)
    assert report["shortest_qualified_horizon_minutes"] == 1
    assert 1 in report["qualified_horizons_minutes"]
    assert 2 in report["qualified_horizons_minutes"]
    assert report["by_horizon"]["3"]["qualified_for_promotion"] is False


def test_shadow_report_empty_journal_has_no_qualified_horizon(tmp_path):
    report = build_shadow_report(tmp_path / "missing.jsonl")
    assert report["total_entries"] == 0
    assert report["shortest_qualified_horizon_minutes"] is None
    assert report["qualified_horizons_minutes"] == []
