from datetime import datetime, timedelta, timezone

import pytest

from packages.gexy.live_backtest import replay_live_pipeline, summarize_by_regime, summarize_live_backtest
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot


def _snapshot(ts: datetime, spot: float, local_gex: float) -> MarketSnapshot:
    expiry = ts + timedelta(days=1)
    options = (
        OptionSnapshot("L", spot - 10, expiry, call_gamma=-20.0, put_gamma=0.0),
        OptionSnapshot("M", spot, expiry, call_gamma=local_gex, put_gamma=0.0),
        OptionSnapshot("U", spot + 10, expiry, call_gamma=40.0, put_gamma=0.0),
    )
    return MarketSnapshot(ts, spot, 0.20, options)


def test_replay_uses_strictly_future_spot() -> None:
    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    snapshots = [
        _snapshot(start + timedelta(minutes=5 * i), 6500 + i * 2, 10.0)
        for i in range(4)
    ]
    points = replay_live_pipeline(snapshots, horizon_steps=2, horizon_minutes=10)
    assert len(points) == 2
    assert points[0].spot == 6500
    assert points[0].future_spot == 6504
    assert points[0].actual_move == 4


def test_summary_scores_direction_error_and_calibration() -> None:
    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    snapshots = [
        _snapshot(start + timedelta(minutes=5 * i), spot, 10.0)
        for i, spot in enumerate((6500, 6504, 6508, 6506))
    ]
    points = replay_live_pipeline(snapshots, horizon_steps=1, horizon_minutes=5)
    summary = summarize_live_backtest(points)
    assert summary.samples == 3
    assert 0.0 <= summary.directional_accuracy <= 1.0
    assert summary.mean_absolute_error >= 0.0
    assert summary.root_mean_squared_error >= 0.0
    assert summary.calibration_gap == pytest.approx(summary.mean_confidence - summary.directional_accuracy)


def test_summary_by_regime_partitions_points() -> None:
    start = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    snapshots = [
        _snapshot(start, 6500, 10.0),
        _snapshot(start + timedelta(minutes=5), 6502, -10.0),
        _snapshot(start + timedelta(minutes=10), 6501, 10.0),
    ]
    points = replay_live_pipeline(snapshots, horizon_steps=1, horizon_minutes=5)
    by_regime = summarize_by_regime(points)
    assert set(by_regime).issubset({"positive_gamma_mean_reversion", "negative_gamma_acceleration"})
    assert sum(summary.samples for summary in by_regime.values()) == len(points)
