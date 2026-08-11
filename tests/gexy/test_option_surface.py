from datetime import datetime, timezone

from packages.gexy.market_adapter import OptionSnapshot
from packages.gexy.option_surface import aggregate_surface


def test_surface_aggregates_greeks_and_oi_by_strike() -> None:
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    options = [
        OptionSnapshot("SPX", 6500, expiry, call_open_interest=100, put_open_interest=80, call_gamma=2, put_gamma=-1, call_vanna=3, put_vanna=-1, call_charm=4, put_charm=-2),
        OptionSnapshot("SPX", 6550, expiry, call_open_interest=200, put_open_interest=20, call_gamma=1, put_gamma=-0.5),
    ]
    surface = aggregate_surface(options)
    assert surface.total_gex == 1.5
    assert surface.total_vanna == 2
    assert surface.total_charm == 2
    assert len(surface.strikes) == 2
    assert surface.call_wall == 6550
