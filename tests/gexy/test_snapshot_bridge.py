from datetime import datetime, timezone

from packages.gexy.feature_engine import build_feature_state
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot
from packages.gexy.recording import JsonlRecorder
from packages.gexy.snapshot_bridge import record_feature_state


def test_record_feature_state_persists_pressure(tmp_path):
    timestamp = datetime(2026, 8, 12, 20, 0, tzinfo=timezone.utc)
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    market = MarketSnapshot(
        timestamp,
        6500.0,
        0.18,
        (
            OptionSnapshot("SPX", 6490.0, expiry, call_gamma=-2.0, put_gamma=1.0),
            OptionSnapshot("SPX", 6510.0, expiry, call_gamma=3.0, put_gamma=-1.0),
        ),
    )
    state = build_feature_state(market, spot_change=1.0, iv_change=0.01)
    recorder = JsonlRecorder(tmp_path / "snapshots.jsonl")

    record_feature_state(recorder, timestamp=timestamp, spot=market.spot, feature_state=state)
    row = list(recorder.read())[0]

    assert row.total_gex == state.total_gex
    assert row.gamma_flip == state.gamma_flip
    assert row.hedge_demand == state.hedge_pressure.total_pressure
    assert row.positioning_confidence == state.hedge_pressure.confidence
