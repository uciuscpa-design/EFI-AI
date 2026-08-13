from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .data import FeatureSnapshot
from .gex import calculate_gex_by_strike
from .hedge import estimate_hedge_pressure
from .levels import detect_levels
from .models import OptionContract


@dataclass(frozen=True)
class GEXYFeatureVector:
    timestamp: datetime
    spot: float
    es: float | None
    total_gex: float
    gamma_flip: float | None
    call_wall: float | None
    put_wall: float | None
    gamma_component: float
    vanna_component: float
    charm_component: float
    estimated_hedge_demand: float
    hedge_direction: str
    positioning_confidence: float


def build_feature_vector(
    snapshot: FeatureSnapshot,
    contracts: list[OptionContract],
    *,
    positioning_confidence: float = 0.0,
) -> GEXYFeatureVector:
    """Build a point-in-time feature vector without using future observations."""
    if not 0.0 <= positioning_confidence <= 1.0:
        raise ValueError("positioning_confidence must be between 0 and 1")
    gex = calculate_gex_by_strike(contracts, spot=snapshot.spx.price)
    levels = detect_levels(contracts, snapshot.spx.price)
    pressure = estimate_hedge_pressure(
        contracts,
        spot=snapshot.spx.price,
        price_change=0.0,
        iv_change=0.0,
        elapsed_years=0.0,
    )
    return GEXYFeatureVector(
        timestamp=snapshot.timestamp,
        spot=snapshot.spx.price,
        es=snapshot.es.price if snapshot.es else None,
        total_gex=gex.total,
        gamma_flip=levels.gamma_flip,
        call_wall=levels.call_wall,
        put_wall=levels.put_wall,
        gamma_component=pressure.gamma_component,
        vanna_component=pressure.vanna_component,
        charm_component=pressure.charm_component,
        estimated_hedge_demand=pressure.estimated_hedge_demand,
        hedge_direction=pressure.direction,
        positioning_confidence=positioning_confidence,
    )
