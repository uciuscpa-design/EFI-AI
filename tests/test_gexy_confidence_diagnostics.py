import json
from datetime import datetime, timedelta, timezone

from packages.gexy.confidence_diagnostics import (
    RAW_UPPER_CAP_THRESHOLD,
    build_confidence_diagnostics,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry


def _prediction(*, direction: str, confidence: float, expected_move: float) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=expected_move,
        primary_target=None,
        invalidation_level=None,
        confidence=confidence,
        horizon_minutes=5,
        regime="negative_gamma_acceleration",
    )


def _log_line(
    timestamp: datetime,
    *,
    spot: float,
    slope: float,
    hedge_acceleration: float,
    lower_distance: float = 20.0,
    upper_distance: float = 10.0,
) -> str:
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
                    "hedge_acceleration": hedge_acceleration,
                    "distance_to_flip": None,
                    "distance_to_lower_wall": lower_distance,
                    "distance_to_upper_wall": upper_distance,
                },
            },
        }
    )


def _append_row(
    *,
    journal,
    timestamp: datetime,
    spot: float,
    direction: str,
    confidence: float,
    expected_move: float,
    realized_move: float,
) -> None:
    entry = make_entry(
        created_at=timestamp,
        spot=spot,
        prediction=_prediction(
            direction=direction,
            confidence=confidence,
            expected_move=expected_move,
        ),
        model_version="confidence-test",
    )
    append_entry(
        journal,
        resolve_entry(
            entry,
            resolved_at=entry.due_at,
            realized_spot=spot + realized_move,
        ),
    )


def test_diagnostic_confirms_mechanical_upper_cap_saturation(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    log = tmp_path / "session.log"
    start = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    lines = []

    for index in range(8):
        timestamp = start + timedelta(minutes=index)
        spot = 6000.0 + index
        slope = 100_000_000.0 if index % 2 == 0 else -100_000_000.0
        lines.append(
            _log_line(
                timestamp,
                spot=spot,
                slope=slope,
                hedge_acceleration=200.0,
            )
        )
        direction = "up" if slope > 0 else "down"
        _append_row(
            journal=journal,
            timestamp=timestamp,
            spot=spot,
            direction=direction,
            confidence=0.95,
            expected_move=5.0,
            realized_move=1.0 if index % 3 else -1.0,
        )

    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = build_confidence_diagnostics(
        journal_path=journal,
        log_paths=[log],
        horizons=(5,),
    )

    overall = report["overall"]
    assert report["status"] == "ok"
    assert overall["saturation_confirmed"] is True
    assert overall["reported_confidence"]["unique_rounded_6dp"] == [0.95]
    assert overall["raw_score"]["min"] > RAW_UPPER_CAP_THRESHOLD
    assert overall["raw_score"]["fraction_at_or_above_upper_cap_threshold"] == 1.0
    assert overall["components"]["median_slope_share_of_structure"] > 0.999
    assert overall["predicted_counts"] == {"up": 4, "down": 4, "flat": 0}
    assert overall["by_predicted_direction"]["up"]["rows"] == 4
    assert overall["by_predicted_direction"]["down"]["rows"] == 4
    assert sum(bucket["rows"] for bucket in overall["accuracy_by_raw_quartile"]) == 8
    assert sum(
        bucket["predicted_counts"]["up"] + bucket["predicted_counts"]["down"]
        for bucket in overall["accuracy_by_raw_quartile"]
    ) == 8
    assert report["production_predictor_changed"] is False
    assert report["execution_authorized"] is False


def test_diagnostic_does_not_claim_saturation_for_small_structure(tmp_path):
    journal = tmp_path / "shadow.jsonl"
    log = tmp_path / "session.log"
    start = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    lines = []

    for index in range(4):
        timestamp = start + timedelta(minutes=index)
        spot = 6000.0 + index
        lines.append(
            _log_line(
                timestamp,
                spot=spot,
                slope=1.0,
                hedge_acceleration=1.0,
                lower_distance=20.0,
                upper_distance=20.0,
            )
        )
        _append_row(
            journal=journal,
            timestamp=timestamp,
            spot=spot,
            direction="down",
            confidence=0.05,
            expected_move=-1.0,
            realized_move=-1.0,
        )

    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = build_confidence_diagnostics(
        journal_path=journal,
        log_paths=[log],
        horizons=(5,),
    )

    overall = report["overall"]
    assert overall["saturation_confirmed"] is False
    assert overall["reported_confidence"]["upper_cap_fraction"] == 0.0
    assert overall["raw_score"]["fraction_at_or_above_upper_cap_threshold"] == 0.0
    assert overall["predicted_counts"] == {"up": 0, "down": 4, "flat": 0}
    assert overall["by_predicted_direction"]["down"]["rows"] == 4
    assert overall["by_predicted_direction"]["up"]["status"] == "no_rows"
