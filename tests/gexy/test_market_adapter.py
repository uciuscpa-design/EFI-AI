from datetime import datetime, timezone

from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot


def test_market_snapshot_contains_point_in_time_option_chain() -> None:
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    option = OptionSnapshot(
        symbol="SPX",
        strike=6500,
        expiry=expiry,
        call_open_interest=100,
        put_open_interest=120,
        call_gamma=0.02,
        put_gamma=-0.018,
        call_vanna=0.01,
        put_vanna=-0.008,
        call_charm=0.002,
        put_charm=-0.001,
        implied_volatility=0.18,
    )
    snapshot = MarketSnapshot(expiry, 6500, 0.18, (option,))
    assert snapshot.options[0].strike == 6500
    assert snapshot.iv == 0.18
