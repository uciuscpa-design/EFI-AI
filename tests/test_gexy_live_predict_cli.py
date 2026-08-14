import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from packages.gexy.gax_features import GAXFeatures
from packages.gexy.gax_shadow_journal import load_gax_shadows
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.multi_horizon import MultiHorizonPrediction
from packages.gexy.prediction_journal import load_entries
from packages.gexy.surface_features import GEXSurfaceFeatures


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_live_predict.py"
SPEC = importlib.util.spec_from_file_location("gexy_live_predict", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_paper_key_shape_rejects_non_pk(monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "YO1234567890")
    assert MODULE._paper_key_shape_is_plausible() is False


def test_paper_key_shape_accepts_plausible_pk(monkeypatch):
    monkeypatch.setenv("APCA_API_KEY_ID", "PK123456789012345678")
    assert MODULE._paper_key_shape_is_plausible() is True
    meta = MODULE._credential_meta()
    assert meta["key_prefix"] == "PK"
    assert meta["key_length"] == 20


def _prediction(horizon: int) -> LivePrediction:
    return LivePrediction(
        direction="down",
        expected_move_points=-3.0,
        primary_target=7740.0,
        invalidation_level=7733.6,
        confidence=0.6,
        horizon_minutes=horizon,
        regime="positive_gamma_mean_reversion",
    )


def test_main_emits_and_journals_multi_horizon_bundle(monkeypatch, tmp_path, capsys):
    forecasts = tuple(_prediction(horizon) for horizon in (5, 15, 30, 60))
    surface = GEXSurfaceFeatures(
        spot=7749.2,
        flip_level=7733.6,
        lower_wall=7740.0,
        upper_wall=7760.0,
        distance_to_flip=15.6,
        distance_to_lower_wall=9.2,
        distance_to_upper_wall=10.8,
        local_gex=168.0,
        local_gex_slope=7.15,
        positive_gamma_regime=True,
        hedge_acceleration=169.9,
    )
    gax = GAXFeatures(
        spot=7749.2,
        local_gax=169.9,
        local_gax_curvature=-12.5,
        magnitude=169.9,
        acceleration_bias="up",
    )
    fake_result = SimpleNamespace(
        timestamp=datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        spot=7749.2,
        quote_times=(),
        pipeline=SimpleNamespace(
            prediction=forecasts[2],
            multi_horizon=MultiHorizonPrediction(forecasts),
            surface_features=surface,
            gax_features=gax,
        ),
    )
    monkeypatch.setenv("APCA_API_KEY_ID", "PK123456789012345678")
    monkeypatch.setattr(MODULE, "predict_from_alpaca", lambda **_: fake_result)
    monkeypatch.setattr(MODULE, "is_alpaca_market_session", lambda _: True)
    journal = tmp_path / "live_predictions.jsonl"
    fine_shadow = tmp_path / "shadow_predictions.jsonl"
    gax_shadow = tmp_path / "gax_shadow.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--journal",
            str(journal),
            "--shadow-journal",
            str(fine_shadow),
            "--gax-shadow-journal",
            str(gax_shadow),
        ],
    )

    assert MODULE.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["predictions_by_horizon"]) == {"5", "15", "30", "60"}
    assert payload["fine_shadow_horizons"] == list(range(1, 61))
    assert payload["gax_shadow"]["source"] == "gex_spatial_derivative_proxy_v1"
    assert payload["journaled_forecasts"] == 4
    assert payload["journaled_fine_shadow_forecasts"] == 60
    assert payload["journaled_gax_shadows"] == 4
    entries = load_entries(journal)
    fine_entries = load_entries(fine_shadow)
    shadows = load_gax_shadows(gax_shadow)
    assert len(entries) == 4
    assert len(fine_entries) == 60
    assert {entry.prediction.horizon_minutes for entry in fine_entries} == set(range(1, 61))
    assert {entry.model_version for entry in fine_entries} == {"gexy-shadow-fine-v1"}
    assert len(shadows) == 4
    assert {item.prediction_id for item in shadows} == {entry.prediction_id for entry in entries}
