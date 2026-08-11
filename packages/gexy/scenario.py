from __future__ import annotations

from dataclasses import dataclass

from .gex import calculate_gex
from .hedge import estimate_hedge_pressure
from .models import HedgePressure, OptionContract


@dataclass(frozen=True)
class ScenarioPoint:
    price: float
    gex: float
    hedge_pressure: HedgePressure


def build_scenario_surface(
    contracts: list[OptionContract],
    *,
    prices: list[float],
    volatility_change: float = 0.0,
    dt: float = 0.0,
) -> list[ScenarioPoint]:
    """Evaluate GEX and first-order hedge pressure at hypothetical prices."""
    points: list[ScenarioPoint] = []
    for price in prices:
        snapshot = calculate_gex(contracts, spot=price)
        pressure = estimate_hedge_pressure(
            contracts,
            spot=price,
            price_change=0.0,
            volatility_change=volatility_change,
            time_change=dt,
        )
        points.append(ScenarioPoint(price=price, gex=snapshot.total, hedge_pressure=pressure))
    return points
