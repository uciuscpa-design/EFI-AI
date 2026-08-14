import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_finish_check.py"
SPEC = importlib.util.spec_from_file_location("gexy_finish_check", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _entry(horizon: int):
    return make_entry(
        created_at=datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc),
        spot=6500.0,
        prediction=LivePrediction(
            direction="down",
            expected_move_points=-2.0,
            primary_target=6498.0,
            invalidation_level=6502.0,
            confidence=0.7,
            horizon_minutes=horizon,
            regime="test",
        ),
        model_version="test",
    )


def test_finish_check_is_ready_with_code_and_data(tmp_path, monkeypatch):
    ui = tmp_path / "index.html"
    launcher = tmp_path / "launch.ps1"
    backtest = tmp_path / "backtest.py"
    live = tmp_path / "live.jsonl"
    shadow = tmp_path / "shadow.jsonl"
    for path in (ui, launcher, backtest):
        path.write_text("ok", encoding="utf-8")
    append_entry(live, _entry(5))
    append_entry(shadow, _entry(1))
    monkeypatch.setattr(MODULE, "UI_PATH", ui)
    monkeypatch.setattr(MODULE, "LAUNCHER_PATH", launcher)
    monkeypatch.setattr(MODULE, "BACKTEST_PATH", backtest)
    monkeypatch.setattr(MODULE, "PRODUCTION_JOURNAL", live)
    monkeypatch.setattr(MODULE, "SHADOW_JOURNAL", shadow)

    report = MODULE.build_report(strict_data=True)

    assert report["status"] == "ready"
    assert report["code_ready"] is True
    assert report["data_ready"] is True
    assert report["execution_enabled"] is False
    assert report["production_journal_entries"] == 1
    assert report["shadow_journal_entries"] == 1


def test_finish_check_can_be_code_ready_before_first_data(tmp_path, monkeypatch):
    ui = tmp_path / "index.html"
    launcher = tmp_path / "launch.ps1"
    backtest = tmp_path / "backtest.py"
    for path in (ui, launcher, backtest):
        path.write_text("ok", encoding="utf-8")
    monkeypatch.setattr(MODULE, "UI_PATH", ui)
    monkeypatch.setattr(MODULE, "LAUNCHER_PATH", launcher)
    monkeypatch.setattr(MODULE, "BACKTEST_PATH", backtest)
    monkeypatch.setattr(MODULE, "PRODUCTION_JOURNAL", tmp_path / "missing-live.jsonl")
    monkeypatch.setattr(MODULE, "SHADOW_JOURNAL", tmp_path / "missing-shadow.jsonl")

    report = MODULE.build_report(strict_data=False)

    assert report["status"] == "ready"
    assert report["code_ready"] is True
    assert report["data_ready"] is False
