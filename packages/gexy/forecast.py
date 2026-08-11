from __future__ import annotations

from dataclasses import dataclass
from math import exp

from .models import HedgePressure


@dataclass(frozen=True)
class MovementForecast:
    horizon_minutes: int
    direction_up_probability: float
    direction_down_probability: float
    expected_move_points: float
    expected_absolute_move_points: float
    confidence: float
    regime: str


def forecast_from_pressure(
    pressure: HedgePressure,
    *,
    horizon_minutes: int,
    realized_vol_points_per_sqrt_minute: float,
) -> MovementForecast:
    """Transparent baseline forecast; calibration replaces this heuristic later.

    The pressure value is a flow estimate, not a price target. We normalize it
    against supplied realized-volatility scale and expose the result explicitly
    as a baseline for historical calibration.
    """
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")
    scale = max(realized_vol_points_per_sqrt_minute * (horizon_minutes ** 0.5), 1e-9)
    z = pressure.estimated_hedge_demand / scale
    up = 1.0 / (1.0 + exp(-z))
    down = 1.0 - up
    expected = (up - down) * scale
    confidence = min(1.0, abs(up - 0.5) * 2.0 * pressure.confidence)
    regime = "reinforcing" if pressure.direction in {"buy", "sell"} else "neutral"
    return MovementForecast(
        horizon_minutes=horizon_minutes,
        direction_up_probability=up,
        direction_down_probability=down,
        expected_move_points=expected,
        expected_absolute_move_points=abs(expected),
        confidence=confidence,
        regime=regime,
    )
