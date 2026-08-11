from datetime import datetime, timedelta, timezone

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.multihorizon import run_horizons


def row(i: int) -> ResearchRow:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc) + timedelta(minutes=i)
    move = float((i % 5) - 2)
    return ResearchRow(
        timestamp=ts, spot=6500 + move, spot_change=move, iv_change=0.001 * i,
        total_gex=100 + i, gamma_change=0.2 * move, vanna_component=0.1 * move,
        charm_component=-0.05 * move, estimated_hedge_demand=0.3 * move,
        positioning_confidence=0.8, label=make_label(6500 + move, 6500 + move + move, 5),
    )


def test_run_horizons_orders_requested_datasets() -> None:
    rows = [row(i) for i in range(30)]
    result = run_horizons({15: rows, 5: rows})
    assert [item.horizon_minutes for item in result] == [5, 15]
    assert all(len(item.results) == 4 for item in result)
