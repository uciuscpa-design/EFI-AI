from datetime import datetime, timedelta, timezone

from packages.gexy.recording import RecordedSnapshot
from packages.gexy.session_dataset import build_session_rows


def _snap(ts, spot, gex, iv=0.20):
    return RecordedSnapshot(
        timestamp=ts,
        spot=spot,
        iv=iv,
        total_gex=gex,
        total_vanna=10.0,
        total_charm=2.0,
        hedge_demand=3.0,
        positioning_confidence=0.5,
        gamma_flip_distance=5.0,
        data_quality="live",
        source="test",
    )


def test_build_session_rows_uses_only_future_observations():
    t0 = datetime(2026, 8, 13, 13, 30, tzinfo=timezone.utc)
    snaps = [
        _snap(t0, 7750.0, 100.0),
        _snap(t0 + timedelta(minutes=1), 7751.0, 110.0),
        _snap(t0 + timedelta(minutes=2), 7753.0, 120.0),
        _snap(t0 + timedelta(minutes=6), 7758.0, 130.0),
    ]
    rows = build_session_rows(snaps, horizons_minutes=(1, 5))
    one = next(row for row in rows if row.timestamp == snaps[1].timestamp and row.horizon_minutes == 1)
    five = next(row for row in rows if row.timestamp == snaps[1].timestamp and row.horizon_minutes == 5)
    assert one.label.return_points == 2.0
    assert five.label.return_points == 7.0
    assert one.gamma_change == 10.0
    assert one.spot_change == 1.0


def test_build_session_rows_skips_missing_required_features():
    t0 = datetime(2026, 8, 13, 13, 30, tzinfo=timezone.utc)
    first = _snap(t0, 7750.0, 100.0)
    missing = RecordedSnapshot(timestamp=t0 + timedelta(minutes=1), spot=7751.0, total_gex=110.0)
    future = _snap(t0 + timedelta(minutes=2), 7752.0, 120.0)
    rows = build_session_rows([first, missing, future], horizons_minutes=(1,))
    assert all(row.timestamp != missing.timestamp for row in rows)
