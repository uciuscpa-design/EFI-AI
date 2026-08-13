from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from packages.gexy.capture import capture_feature_state
from packages.gexy.recording import JsonlRecorder


def test_capture_records_only_fresh_surface(tmp_path) -> None:
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)
    recorder = JsonlRecorder(tmp_path / "capture.jsonl")
    state = SimpleNamespace(
        total_gex=123.0,
        gamma_flip=7750.0,
        hedge_pressure=SimpleNamespace(total_pressure=-8.0, confidence=0.7),
        data_quality="indicative",
    )

    result = capture_feature_state(
        recorder,
        observation_time=now,
        spot=7752.0,
        feature_state=state,
        option_quote_times=(now - timedelta(seconds=10), now - timedelta(seconds=20)),
    )

    assert result.recorded is True
    rows = list(recorder.read())
    assert len(rows) == 1
    assert rows[0].hedge_demand == -8.0
    assert rows[0].positioning_confidence == 0.7


def test_capture_rejects_stale_surface(tmp_path) -> None:
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)
    recorder = JsonlRecorder(tmp_path / "capture.jsonl")
    state = SimpleNamespace(total_gex=123.0, gamma_flip=7750.0)

    result = capture_feature_state(
        recorder,
        observation_time=now,
        spot=7752.0,
        feature_state=state,
        option_quote_times=(now - timedelta(minutes=4),),
    )

    assert result.recorded is False
    assert result.data_quality == "stale"
    assert list(recorder.read()) == []


def test_capture_rejects_empty_surface(tmp_path) -> None:
    recorder = JsonlRecorder(tmp_path / "capture.jsonl")
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)

    result = capture_feature_state(
        recorder,
        observation_time=now,
        spot=7752.0,
        feature_state=SimpleNamespace(),
        option_quote_times=(),
    )

    assert result.recorded is False
    assert result.data_quality == "insufficient_data"
