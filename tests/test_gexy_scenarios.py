from datetime import datetime, timezone

import pytest

from packages.gexy.models import OptionContract
from packages.gexy.scenarios import apply_scenario, scenario_sensitivity


def _option(option_type: str, dealer_sign: float = -1.0) -> OptionContract:
    return OptionContract(
        symbol=f"X-{option_type}",
        underlying="SPX",
        strike=7750.0,
        expiration=datetime(2026, 8, 21, tzinfo=timezone.utc),
        option_type=option_type,
        open_interest=1000.0,
        gamma=0.003,
        dealer_sign=dealer_sign,
        confidence=1.0,
    )


def test_apply_scenario_sets_expected_signs():
    options = [_option("call"), _option("put")]
    assert {o.dealer_sign for o in apply_scenario(options, "long_gamma")} == {1.0}
    assert {o.dealer_sign for o in apply_scenario(options, "short_gamma")} == {-1.0}
    mixed = apply_scenario(options, "mixed")
    assert mixed[0].dealer_sign == 1.0
    assert mixed[1].dealer_sign == -1.0


def test_long_gamma_sells_rally_and_buys_dip():
    rows = scenario_sensitivity([_option("call")], reference_spot=7750.0, moves=(-10.0, 10.0), scenarios=("long_gamma",))
    assert rows[0].hedge_direction == "buy"
    assert rows[1].hedge_direction == "sell"


def test_short_gamma_buys_rally_and_sells_dip():
    rows = scenario_sensitivity([_option("call")], reference_spot=7750.0, moves=(-10.0, 10.0), scenarios=("short_gamma",))
    assert rows[0].hedge_direction == "sell"
    assert rows[1].hedge_direction == "buy"


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        apply_scenario([_option("call")], "magic")
