from datetime import datetime, timedelta, timezone

from packages.gexy.dataset import assemble_rows
from packages.gexy.dynamic_features import DynamicFeatureRow
from packages.gexy.replay import MarketSnapshot


def test_assemble_rows_joins_future_labels() -> None:
    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    feature = DynamicFeatureRow(
        timestamp=start,
        spot=6500,
        spot_change=0,
        iv_change=0.0,
        time_change_minutes=1,
        total_gex=100,
        gamma_change=0,
        vanna_component=1,
        charm_component=-1,
        estimated_hedge_demand=2,
        positioning_confidence=0.8,
    )
    prices = [
        MarketSnapshot(start, 6500),
        MarketSnapshot(start + timedelta(minutes=5), 6507),
    ]
    rows = assemble_rows([feature], prices, horizon_minutes=5)
    assert len(rows) == 1
    assert rows[0].label.return_points == 7
