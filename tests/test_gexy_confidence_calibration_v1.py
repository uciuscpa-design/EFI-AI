from datetime import date, datetime, timedelta, timezone

import pytest

from packages.gexy.confidence_calibration_v1 import (
    MODEL_ID,
    build_confidence_calibration_v1_report,
    fit_selection_model,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry


def _prediction(direction: str, *, horizon: int = 5) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=1.0 if direction == "up" else -1.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.95,
        horizon_minutes=horizon,
        regime="negative_gamma_acceleration",
    )


def _resolved_entry(
    *,
    session_date: date,
    index: int,
    direction: str,
    hit: bool,
    horizon: int = 5,
):
    created_at = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        14,
        0,
        tzinfo=timezone.utc,
    ) + timedelta(seconds=index)
    spot = 6000.0 + index / 100.0
    prediction = _prediction(direction, horizon=horizon)
    entry = make_entry(
        created_at=created_at,
        spot=spot,
        prediction=prediction,
        model_version="confidence-calibration-test",
    )
    if direction == "up":
        realized_move = 1.0 if hit else -1.0
    else:
        realized_move = -1.0 if hit else 1.0
    return resolve_entry(
        entry,
        resolved_at=entry.due_at,
        realized_spot=spot + realized_move,
    )


def _append_group(
    journal,
    *,
    session_date: date,
    direction: str,
    rows: int,
    hits: int,
    index_offset: int,
) -> None:
    for index in range(rows):
        append_entry(
            journal,
            _resolved_entry(
                session_date=session_date,
                index=index_offset + index,
                direction=direction,
                hit=index < hits,
            ),
        )


def test_fit_selection_model_uses_jeffreys_smoothed_direction_cells():
    entries = []
    for index in range(20):
        entries.append(
            _resolved_entry(
                session_date=date(2026, 8, 14),
                index=index,
                direction="down",
                hit=index < 15,
            )
        )
        entries.append(
            _resolved_entry(
                session_date=date(2026, 8, 14),
                index=100 + index,
                direction="up",
                hit=index < 5,
            )
        )

    model = fit_selection_model(entries)
    assert model["model_id"] == MODEL_ID
    assert model["selection_rows"] == 40
    assert model["cells"]["5:down"]["posterior_probability_correct"] == pytest.approx(15.5 / 21.0)
    assert model["cells"]["5:up"]["posterior_probability_correct"] == pytest.approx(5.5 / 21.0)
    assert model["cells"]["5:down"]["minimum_rows_met"] is True
    assert model["fingerprint_sha256"]


def test_selection_session_is_fit_only_and_never_validation(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    _append_group(
        journal,
        session_date=date(2026, 8, 14),
        direction="down",
        rows=40,
        hits=32,
        index_offset=0,
    )
    _append_group(
        journal,
        session_date=date(2026, 8, 14),
        direction="up",
        rows=40,
        hits=8,
        index_offset=100,
    )

    report = build_confidence_calibration_v1_report(journal_path=journal)
    assert report["status"] == "awaiting_independent_sessions"
    assert report["selection_session_is_validation"] is False
    assert report["selection_fit_diagnostic"]["scored"] == 80
    assert report["independent_sessions"] == []
    assert report["promotion_gate"]["met"] is False
    assert report["production_confidence_replacement_authorized"] is False
    assert report["production_direction_change_authorized"] is False
    assert report["execution_authorized"] is False


def test_one_good_future_session_improves_brier_but_cannot_pass_gate(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    _append_group(
        journal,
        session_date=date(2026, 8, 14),
        direction="down",
        rows=40,
        hits=32,
        index_offset=0,
    )
    _append_group(
        journal,
        session_date=date(2026, 8, 14),
        direction="up",
        rows=40,
        hits=8,
        index_offset=100,
    )
    _append_group(
        journal,
        session_date=date(2026, 8, 17),
        direction="down",
        rows=30,
        hits=24,
        index_offset=200,
    )
    _append_group(
        journal,
        session_date=date(2026, 8, 17),
        direction="up",
        rows=30,
        hits=6,
        index_offset=300,
    )

    report = build_confidence_calibration_v1_report(journal_path=journal)
    session = report["independent_sessions"][0]
    assert report["status"] == "collecting_independent_evidence"
    assert session["informative"] is True
    assert session["positive_calibration_result"] is True
    assert session["brier_improvement_vs_horizon_only"] > 0.0
    assert session["brier_improvement_vs_0_5"] > 0.0
    assert report["promotion_gate"]["positive_session_count"] == 1
    assert report["promotion_gate"]["met"] is False
