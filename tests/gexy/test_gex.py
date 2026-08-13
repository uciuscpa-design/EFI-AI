from datetime import datetime, timezone

import pytest

from packages.gexy.gex import calculate_gex_by_strike, scenario_gex
from packages.gexy.hedge import estimate_hedge_pressure
from packages.gexy.models import OptionContract


@pytest.fixture
def options() -> list[OptionContract]:
    expiry = datetime(2026, 8, 14, tzinfo=timezone.utc)
    return [
        OptionContract("C6500", "SPX", 6500, expiry, "call", 100, 0.0005, dealer_sign=-1, confidence=1),
        OptionContract("P6450", "SPX", 6450, expiry, "put", 200, 0.0004, dealer_sign=-1, confidence=1),
    ]


def test_gex_is_grouped_by_strike(options: list[OptionContract]) -> None:
    snapshot = calculate_gex_by_strike(options, 6500)
    assert set(snapshot.by_strike) == {6450, 6500}
    assert snapshot.total < 0


def test_scenario_gex_changes_with_spot(options: list[OptionContract]) -> None:
    result = scenario_gex(options, [6400, 6500, 6600])
    assert list(result) == [6400, 6500, 6600]
    assert all(isinstance(value, float) for value in result.values())


def test_negative_dealer_gamma_requires_selling_on_down_move(options: list[OptionContract]) -> None:
    pressure = estimate_hedge_pressure(options, 6500, price_change=-10)
    assert pressure.estimated_hedge_demand < 0
    assert pressure.direction == "sell_underlying"


def test_invalid_spot_is_rejected(options: list[OptionContract]) -> None:
    with pytest.raises(ValueError):
        calculate_gex_by_strike(options, 0)
