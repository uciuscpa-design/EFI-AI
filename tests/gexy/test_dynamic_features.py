from datetime import datetime, timezone

from packages.gexy.dynamic_features import build_dynamic_row


def test_dynamic_row_calculates_changes() -> None:
    row = build_dynamic_row(
        timestamp=datetime(2026, 8, 10, 13, 35, tzinfo=timezone.utc),
        spot=6505,
        previous_spot=6500,
        iv=0.18,
        previous_iv=0.17,
        total_gex=120,
        previous_gex=100,
        vanna_component=3,
        charm_component=-1,
        estimated_hedge_demand=8,
        positioning_confidence=1.4,
        elapsed_minutes=5,
    )
    assert row.spot_change == 5
    assert row.iv_change == 0.01
    assert row.gamma_change == 20
    assert row.positioning_confidence == 1.0
