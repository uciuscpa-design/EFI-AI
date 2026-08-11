from datetime import datetime, timezone

from packages.gexy.live_bridge import snapshot_to_row
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot


def test_snapshot_to_row_has_live_features_and_neutral_label() -> None:
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    snapshot = MarketSnapshot(
        datetime(2026, 8, 10, 14, tzinfo=timezone.utc),
        6502,
        0.19,
        (OptionSnapshot("SPX", 6500, expiry, call_gamma=2, put_gamma=-1),),
    )
    row = snapshot_to_row(snapshot, previous_spot=6500, previous_iv=0.18)
    assert row.spot == 6502
    assert row.spot_change == 2
    assert row.iv_change == 0.01
    assert row.total_gex == 1
    assert row.label == 0
