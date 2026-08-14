from datetime import datetime, timezone

from fastapi.testclient import TestClient

from apps.gexy_api import main as api_main
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry


def _prediction(horizon: int, direction: str = "down") -> LivePrediction:
    move = -5.0 if direction == "down" else 5.0
    return LivePrediction(
        direction=direction,
        expected_move_points=move,
        primary_target=6495.0 if direction == "down" else 6505.0,
        invalidation_level=6502.0,
        confidence=0.8,
        horizon_minutes=horizon,
        regime="negative_gamma_acceleration",
    )


def _entry(horizon: int, *, spot: float = 6500.0, model_version: str = "test"):
    return make_entry(
        created_at=datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc),
        spot=spot,
        prediction=_prediction(horizon),
        model_version=model_version,
    )


def test_live_history_auto_uses_shadow_for_fine_horizon(tmp_path, monkeypatch):
    live = tmp_path / "live.jsonl"
    shadow = tmp_path / "shadow.jsonl"
    append_entry(shadow, _entry(1, model_version="shadow-test"))
    monkeypatch.setattr(api_main, "LIVE_JOURNAL", live)
    monkeypatch.setattr(api_main, "SHADOW_JOURNAL", shadow)

    response = TestClient(api_main.app).get("/v1/live/history?horizon=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "shadow"
    assert payload["horizon_minutes"] == 1
    assert payload["count"] == 1
    assert payload["points"][0]["forecast_spot"] == 6495.0
    assert payload["points"][0]["model_version"] == "shadow-test"


def test_live_history_auto_uses_production_for_standard_horizon(tmp_path, monkeypatch):
    live = tmp_path / "live.jsonl"
    shadow = tmp_path / "shadow.jsonl"
    append_entry(live, _entry(5, model_version="live-test"))
    append_entry(shadow, _entry(5, model_version="shadow-test"))
    monkeypatch.setattr(api_main, "LIVE_JOURNAL", live)
    monkeypatch.setattr(api_main, "SHADOW_JOURNAL", shadow)

    response = TestClient(api_main.app).get("/v1/live/history?horizon=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "production"
    assert payload["count"] == 1
    assert payload["points"][0]["model_version"] == "live-test"


def test_live_latest_returns_404_without_matching_predictions(tmp_path, monkeypatch):
    live = tmp_path / "live.jsonl"
    shadow = tmp_path / "shadow.jsonl"
    live.write_text("", encoding="utf-8")
    shadow.write_text("", encoding="utf-8")
    monkeypatch.setattr(api_main, "LIVE_JOURNAL", live)
    monkeypatch.setattr(api_main, "SHADOW_JOURNAL", shadow)

    response = TestClient(api_main.app).get("/v1/live/latest?horizon=30")

    assert response.status_code == 404
    assert "no 30m GEXY predictions" in response.json()["detail"]


def test_live_horizons_exposes_one_minute_grid():
    response = TestClient(api_main.app).get("/v1/live/horizons")

    assert response.status_code == 200
    payload = response.json()
    assert payload["production"] == [5, 15, 30, 60]
    assert payload["shadow"][0] == 1
    assert payload["shadow"][-1] == 60
    assert len(payload["shadow"]) == 60
