import json
from datetime import datetime, timedelta, timezone

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry
from packages.gexy.shadow_feature_ablation import (
    build_shadow_feature_ablation,
    join_shadow_rows,
    load_feature_observations,
)


def _prediction(direction: str, horizon: int = 5) -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=2.0 if direction == "up" else -2.0,
        primary_target=None,
        invalidation_level=None,
        confidence=0.95,
        horizon_minutes=horizon,
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
                    "distance_to_flip": 5.0 if slope > 0 else -5.0,
                    "distance_to_lower_wall": 20.0,
                    "distance_to_upper_wall": 10.0,
                },
            },
        }
    )


def test_load_observations_and_join_exact_timestamp(tmp_path):
    start = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    log = tmp_path / "session.log"
    log.write_text(
        "header\n" + _log_line(start, 6000.0, 1.0) + "\n" + _log_line(start + timedelta(minutes=1), 6001.5, -1.0) + "\n",
        encoding="utf-8",
    )
    observations = load_feature_observations([log])
    assert len(observations) == 2
    assert observations[0].spot_momentum_points is None
    assert observations[1].spot_momentum_points == 1.5

    entry = make_entry(created_at=start, spot=6000.0, prediction=_prediction("up"))
    resolved = resolve_entry(entry, resolved_at=entry.due_at, realized_spot=5998.0)
    rows = join_shadow_rows([resolved], observations)
    assert len(rows) == 1
    assert rows[0].observation.local_gex_slope == 1.0


def test_ablation_identifies_inverted_slope_when_direct_branch_is_wrong(tmp_path):
    start = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    log = tmp_path / "session-2026-08-14.log"
    journal = tmp_path / "shadow.jsonl"
    lines = []

    for index in range(10):
        timestamp = start + timedelta(minutes=index)
        slope = 1.0 if index % 2 == 0 else -1.0
        spot = 6000.0 + index
        lines.append(_log_line(timestamp, spot, slope))
        current_direction = "up" if slope > 0 else "down"
        entry = make_entry(
            created_at=timestamp,
            spot=spot,
            prediction=_prediction(current_direction),
            model_version="test-shadow",
        )
        realized_spot = spot - 1.0 if slope > 0 else spot + 1.0
        append_entry(
            journal,
            resolve_entry(entry, resolved_at=entry.due_at, realized_spot=realized_spot),
        )

    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = build_shadow_feature_ablation(journal_path=journal, log_paths=[log], horizons=(5,))

    assert report["status"] == "ok"
    assert report["matched_coverage"] == 1.0
    assert report["candidate_rules"]["current_prediction"]["directional_accuracy"] == 0.0
    assert report["candidate_rules"]["slope_inverted"]["directional_accuracy"] == 1.0
    assert report["features"]["local_gex_slope"]["chronological_median_rule"]["status"] == "ok"
    assert report["session_count"] == 1
