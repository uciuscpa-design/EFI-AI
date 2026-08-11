from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .hedge_pressure import HedgePressure, estimate_hedge_pressure
from .market_adapter import MarketSnapshot
from .option_surface import PositioningSurface, aggregate_surface


@dataclass(frozen=True)
class GexyFeatureState:
    timestamp: datetime
    spot: float
    iv: float | None
    total_gex: float
    total_vanna: float
    total_charm: float
    call_wall: float | None
    put_wall: float | None
    gamma_flip: float | None
    gamma_flip_distance: float | None
    hedge_pressure: HedgePressure


def estimate_gamma_flip(snapshot: MarketSnapshot) -> float | None:
    surface = aggregate_surface(snapshot.options)
    if len(surface.strikes) < 2:
        return None
    strikes = surface.strikes
    # Approximate the zero-crossing of cumulative strike GEX. This is a
    # baseline estimator; production research should validate the definition
    # and use a consistent dealer-sign convention upstream.
    cumulative = 0.0
    previous = None
    for point in strikes:
        current = cumulative + point.gex
        if previous is not None and previous[1] * current <= 0:
            x0, y0 = previous
            x1, y1 = point.strike, current
            if y1 == y0:
                return x0
            return x0 + (0.0 - y0) * (x1 - x0) / (y1 - y0)
        cumulative = current
        previous = (point.strike, cumulative)
    return None


def build_feature_state(
    snapshot: MarketSnapshot,
    *,
    spot_change: float = 0.0,
    iv_change: float = 0.0,
    dt_minutes: float = 1.0,
) -> GexyFeatureState:
    surface: PositioningSurface = aggregate_surface(snapshot.options)
    flip = estimate_gamma_flip(snapshot)
    pressure = estimate_hedge_pressure(
        total_gex=surface.total_gex,
        total_vanna=surface.total_vanna,
        total_charm=surface.total_charm,
        spot_change=spot_change,
        iv_change=iv_change,
        dt_minutes=dt_minutes,
    )
    return GexyFeatureState(
        timestamp=snapshot.timestamp,
        spot=snapshot.spot,
        iv=snapshot.iv,
        total_gex=surface.total_gex,
        total_vanna=surface.total_vanna,
        total_charm=surface.total_charm,
        call_wall=surface.call_wall,
        put_wall=surface.put_wall,
        gamma_flip=flip,
        gamma_flip_distance=None if flip is None else snapshot.spot - flip,
        hedge_pressure=pressure,
    )
