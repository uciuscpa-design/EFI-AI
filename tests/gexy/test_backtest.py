from datetime import datetime, timedelta, timezone

from packages.gexy.backtest import chronological_points, chronological_split
from packages.gexy.market_adapter import MarketSnapshot


def test_split_preserves_time_order() -> None:
    result = chronological_split(list(range(10)), train_fraction=0.6, validation_fraction=0.2)
    assert result.train == [0, 1, 2, 3, 4, 5]
    assert result.validation == [6, 7]
    assert result.test == [8, 9]


def test_forward_labels_use_future_only() -> None:
    base = datetime(2026, 8, 10, tzinfo=timezone.utc)
    snapshots = [MarketSnapshot(base + timedelta(minutes=i), 6500 + i, None, ()) for i in range(5)]
    points = chronological_points(snapshots, [1, 1, 1, 1, 1], horizon_steps=2, horizon_minutes=2)
    assert len(points) == 3
    assert [p.actual_move for p in points] == [2, 2, 2]
