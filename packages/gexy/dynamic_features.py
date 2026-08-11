from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DynamicFeatureRow:
    timestamp: datetime
    spot: float
    spot_change: float
    iv_change: float
    time_change_minutes: float
    total_gex: float
    gamma_change: float
    vanna_component: float
    charm_component: float
    estimated_hedge_demand: float
    positioning_confidence: float


def build_dynamic_row(
    *,
    timestamp: datetime,
    spot: float,
    previous_spot: float,
    iv: float | None,
    previous_iv: float | None,
    total_gex: float,
    previous_gex: float,
    vanna_component: float,
    charm_component: float,
    estimated_hedge_demand: float,
    positioning_confidence: float,
    elapsed_minutes: float,
) -> DynamicFeatureRow:
    if spot <= 0 or previous_spot <= 0:
        raise ValueError("spot prices must be positive")
    if elapsed_minutes <= 0:
        raise ValueError("elapsed_minutes must be positive")
    iv_change = 0.0 if iv is None or previous_iv is None else iv - previous_iv
    return DynamicFeatureRow(
        timestamp=timestamp,
        spot=spot,
        spot_change=spot - previous_spot,
        iv_change=iv_change,
        time_change_minutes=elapsed_minutes,
        total_gex=total_gex,
        gamma_change=total_gex - previous_gex,
        vanna_component=vanna_component,
        charm_component=charm_component,
        estimated_hedge_demand=estimated_hedge_demand,
        positioning_confidence=max(0.0, min(1.0, positioning_confidence)),
    )
