from __future__ import annotations

from collections import defaultdict
from math import isfinite

from .models import GEXSnapshot, OptionContract


def gamma_exposure(option: OptionContract, spot: float | None = None) -> float:
    """Return signed dollar gamma exposure per 1% underlying move.

    The sign is supplied by the dealer-position hypothesis. The conventional
    scaling is gamma * OI * multiplier * spot^2 * 0.01.
    """
    s = spot if spot is not None else option.strike
    if s <= 0:
        raise ValueError("spot must be positive")
    value = option.dealer_sign * option.confidence * option.gamma * option.open_interest * option.multiplier * s * s * 0.01
    if not isfinite(value):
        raise ValueError("non-finite gamma exposure")
    return value


def calculate_gex_by_strike(options: list[OptionContract], spot: float) -> GEXSnapshot:
    if spot <= 0:
        raise ValueError("spot must be positive")
    by_strike: dict[float, float] = defaultdict(float)
    for option in options:
        by_strike[option.strike] += gamma_exposure(option, spot)
    by_strike = dict(sorted(by_strike.items()))
    return GEXSnapshot(spot=spot, by_strike=by_strike, total=sum(by_strike.values()))


def scenario_gex(options: list[OptionContract], prices: list[float]) -> dict[float, float]:
    """Evaluate aggregate signed GEX at hypothetical spot prices."""
    return {price: calculate_gex_by_strike(options, price).total for price in prices}
