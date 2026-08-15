import json
from datetime import date, datetime, timedelta, timezone

from packages.gexy.h5_slope_invert_v1 import (
    HYPOTHESIS_ID,
    build_h5_slope_invert_v1_report,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry


def _prediction(direction: str) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=1.0 if direction == "up" else -1.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.95,
        horizon_minutes=5,
        regime="negative_gamma_acceleration",
    )


def _log_line(timestamp: datetime, spot: float, slope: float) -> str:
    return json.dumps(
        {
            "status": "ok",
            "prediction": {
                "status": "ok",
                "timestamp": timestamp.isoformat(),
                "spot": spot,
                "surface": {
                    "local_gex": -100.0,
                    "local_gex_slope": slope,
                    "hedge_acceleration": slope * 10.0,
                    "distance_to_flip": None,
                    "distance_to_lower_wall": 20.0,
                    "distance_to_upper_wall": 10.0,
                },
            },
        }
    )


def _write_session(
    *,
    journal,
    log,
    session_date: date,
    rows: int = 60,
    frozen_rule_correct: bool = True,
) -> None:
    start = datetime(
        session_date.year,
        session_date.month,
        session_date.day,
        14,
        0,
        tzinfo=timezone.utc,
    )
    lines: list[str] = []
    for index in range(rows):
        timestamp = start + timedelta(minutes=index)
        slope = 1.0 if index % 2 == 0 else -1.0
        spot = 6000.0 + index / 10.0
        lines.append(_log_line(timestamp, spot, slope))

        current_direction = "up" if slope > 0 else "down"
        frozen_direction = "down" if slope > 0 else "up"
        realized_direction = frozen_direction
        if not frozen_rule_correct:
            realized_direction = "up" if frozen_direction == "down" else "down"

        entry = make_entry(
            created_at=timestamp,
            spot=spot,
            prediction=_prediction(current_direction),
            model_version="test-shadow",
        )
        realized_spot = spot + (1.0 if realized_direction == "up" else -1.0)
        append_entry(
            journal,
            resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized_spot),
        )

    log.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_selection_session_is_never_counted_as_independent(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    selection_log = tmp_path / "session-2026-08-14.log"
    _write_session(
        journal=journal,
        log=selection_log,
        session_date=date(2026, 8, 14),
    )

    report = build_h5_slope_invert_v1_report(
        journal_path=journal,
        log_paths=[selection_log],
    )

    assert report["hypothesis_id"] == HYPOTHESIS_ID
    assert report["status"] == "awaiting_independent_sessions"
    assert report["selection_or_earlier_resolved_5m_rows_excluded"] == 60
    assert report["independent_sessions"] == []
    assert report["promotion_gate"]["met"] is False
    assert report["production_predictor_change_authorized"] is False
    assert report["execution_authorized"] is False


def test_two_positive_independent_sessions_meet_shadow_review_gate(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    logs = []
    for session_date in (date(2026, 8, 14), date(2026, 8, 17), date(2026, 8, 18)):
        log = tmp_path / f"session-{session_date.isoformat()}.log"
        _write_session(journal=journal, log=log, session_date=session_date)
        logs.append(log)

    report = build_h5_slope_invert_v1_report(journal_path=journal, log_paths=logs)

    assert report["status"] == "eligible_for_shadow_experiment_review"
    assert len(report["independent_sessions"]) == 2
    assert report["promotion_gate"]["informative_session_count"] == 2
    assert report["promotion_gate"]["positive_lift_session_count"] == 2
    assert report["promotion_gate"]["aggregate"]["frozen_rule"]["directional_accuracy"] == 1.0
    assert report["promotion_gate"]["aggregate"]["always_down"]["directional_accuracy"] == 0.5
    assert report["promotion_gate"]["aggregate"]["lift_vs_always_down"] == 0.5
    assert report["promotion_gate"]["met"] is True
    assert report["production_predictor_change_authorized"] is False
    assert report["execution_authorized"] is False


def test_one_positive_and_one_negative_session_do_not_meet_gate(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    selection_log = tmp_path / "session-2026-08-14.log"
    positive_log = tmp_path / "session-2026-08-17.log"
    negative_log = tmp_path / "session-2026-08-18.log"

    _write_session(journal=journal, log=selection_log, session_date=date(2026, 8, 14))
    _write_session(journal=journal, log=positive_log, session_date=date(2026, 8, 17))
    _write_session(
        journal=journal,
        log=negative_log,
        session_date=date(2026, 8, 18),
        frozen_rule_correct=False,
    )

    report = build_h5_slope_invert_v1_report(
        journal_path=journal,
        log_paths=[selection_log, positive_log, negative_log],
    )

    assert report["status"] == "collecting_independent_evidence"
    assert report["promotion_gate"]["informative_session_count"] == 2
    assert report["promotion_gate"]["positive_lift_session_count"] == 1
    assert report["promotion_gate"]["aggregate"]["lift_vs_always_down"] == 0.0
    assert report["promotion_gate"]["met"] is False
