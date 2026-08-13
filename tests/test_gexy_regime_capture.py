from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from packages.gexy.recording import JsonlRecorder, RecordedSnapshot
from packages.gexy.snapshot_bridge import record_feature_state


@dataclass
class Pressure:
    total_pressure: float = 1.0
    gamma_pressure: float = 1.0
    vanna_pressure: float = 0.0
    charm_pressure: float = 0.0
    confidence: float = 1.0


@dataclass
class FeatureState:
    total_gex: float
    hedge_pressure: Pressure
    total_vanna: float = 0.0
    total_charm: float = 0.0
    iv: float = 0.2
    gamma_flip: float | None = None
    gamma_flip_distance: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    data_quality: str = "live"


def test_first_capture_has_no_regime_and_second_is_point_in_time(tmp_path):
    recorder = JsonlRecorder(tmp_path / "capture.jsonl")
    t0 = datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc)
    record_feature_state(
        recorder,
        timestamp=t0,
        spot=7750.0,
        feature_state=FeatureState(total_gex=1_000_000.0, hedge_pressure=Pressure()),
    )
    record_feature_state(
        recorder,
        timestamp=t0 + timedelta(minutes=1),
        spot=7760.0,
        feature_state=FeatureState(total_gex=1_000_000.0, hedge_pressure=Pressure()),
    )
    rows = list(recorder.read())
    assert rows[0].regime_score is None
    assert rows[1].regime_score is not None
    assert rows[1].regime_score > 0


def test_old_snapshot_without_regime_field_remains_valid():
    row = RecordedSnapshot(timestamp=datetime.now(timezone.utc), spot=7750.0)
    assert row.regime_score is None
