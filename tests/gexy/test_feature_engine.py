from datetime import datetime, timezone

from packages.gexy.feature_engine import build_feature_state, estimate_gamma_flip
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot


def test_feature_state_connects_surface_and_pressure() -> None:
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    options = (
        OptionSnapshot("SPX", 6490, expiry, call_gamma=-2.0, put_gamma=1.0),
        OptionSnapshot("SPX", 6510, expiry, call_gamma=3.0, put_gamma=-1.0),
    )
    snapshot = MarketSnapshot(datetime(2026, 8, 10, tzinfo=timezone.utc), 6500, 0.18, options)
    state = build_feature_state(snapshot, spot_change=1.0, iv_change=0.01)
    assert state.total_gex == 1.0
    assert state.gamma_flip is not None
    assert state.gamma_flip_distance is not None
