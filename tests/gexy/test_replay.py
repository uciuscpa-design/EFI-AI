from datetime import datetime, timedelta, timezone

from packages.gexy.replay import MarketSnapshot, build_forward_labels


def test_forward_labels_use_future_only() -> None:
    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    snapshots = [
        MarketSnapshot(start, 6500),
        MarketSnapshot(start + timedelta(minutes=1), 6501),
        MarketSnapshot(start + timedelta(minutes=5), 6506),
        MarketSnapshot(start + timedelta(minutes=10), 6495),
    ]
    result = build_forward_labels(snapshots, horizon_minutes=5)
    assert result[0].label.return_points == 6
    assert result[0].label.horizon_minutes == 5
