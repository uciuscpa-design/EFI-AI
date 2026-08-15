import json
from datetime import datetime, timedelta, timezone

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry
from packages.gexy.shadow_horizon_holdout import build_horizon_holdout


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


def test_late_holdout_can_confirm_slope_inversion(tmp_path):
    start = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    journal = tmp_path / "shadow.jsonl"
    log = tmp_path / "session.log"
    lines = []

    for index in range(20):
        timestamp = start + timedelta(minutes=index)
        slope = 1.0 if index % 2 == 0 else -1.0
        spot = 6000.0 + index
        current = "up" if slope > 0 else "down"
        lines.append(
            json.dumps(
                {
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
                    }
                }
            )
        )
        entry = make_entry(created_at=timestamp, spot=spot, prediction=_prediction(current))
        realized_spot = spot - 1.0 if slope > 0 else spot + 1.0
        append_entry(journal, resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized_spot))

    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = build_horizon_holdout(journal_path=journal, log_paths=[log], horizons=(5,))
    metrics = report["by_horizon"]["5"]

    assert report["status"] == "ok"
    assert metrics["test"]["slope_inverted"]["directional_accuracy"] == 1.0
    assert metrics["test_lift_vs_always_down"]["slope_inverted"] > 0.0
