from __future__ import annotations

import pytest

from packages.gexy.forward_greeks import (
    black76_greeks,
    fit_forward_discount_from_parity,
    implied_volatility_from_forward_price,
)
from packages.gexy.models import OptionType


def test_parity_fit_recovers_forward_and_discount_factor() -> None:
    forward = 7776.5
    discount = 0.9999
    pairs = []
    for strike, call in [(7700.0, 80.0), (7750.0, 40.0), (7800.0, 12.0), (7850.0, 3.0)]:
        put = call - discount * (forward - strike)
        pairs.append((strike, call, put))

    fit = fit_forward_discount_from_parity(pairs)

    assert fit.forward == pytest.approx(forward, rel=1e-10)
    assert fit.discount_factor == pytest.approx(discount, rel=1e-10)
    assert fit.pair_count == 4
    assert fit.max_abs_residual < 1e-9


def test_parity_fit_is_robust_to_one_bad_pair() -> None:
    forward = 7776.5
    discount = 0.9999
    pairs = []
    for strike, call in [(7700.0, 80.0), (7725.0, 60.0), (7750.0, 40.0), (7775.0, 24.0), (7800.0, 12.0)]:
        put = call - discount * (forward - strike)
        pairs.append((strike, call, put))
    # One stale/wide pair should not move the median-slope fit materially.
    pairs.append((7900.0, 1.0, 150.0))

    fit = fit_forward_discount_from_parity(pairs)

    assert fit.forward == pytest.approx(forward, abs=0.1)
    assert fit.discount_factor == pytest.approx(discount, abs=0.002)


def test_black76_call_put_share_gamma() -> None:
    common = dict(
        forward=7776.5,
        strike=7775.0,
        time_to_expiry_years=6.5 / (365 * 24),
        volatility=0.20,
        discount_factor=0.9999,
    )
    call = black76_greeks(option_type=OptionType.CALL, **common)
    put = black76_greeks(option_type=OptionType.PUT, **common)

    assert call.price > 0
    assert put.price > 0
    assert call.gamma_forward == pytest.approx(put.gamma_forward)
    assert call.delta_forward > 0
    assert put.delta_forward < 0


def test_forward_implied_volatility_round_trip() -> None:
    inputs = dict(
        option_type=OptionType.PUT,
        forward=7776.5,
        strike=7800.0,
        time_to_expiry_years=6.5 / (365 * 24),
        discount_factor=0.9999,
    )
    expected = 0.215
    price = black76_greeks(volatility=expected, **inputs).price

    recovered = implied_volatility_from_forward_price(option_price=price, **inputs)

    assert recovered == pytest.approx(expected, rel=1e-6)
