from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Regime:
    gamma: str
    flip_distance: float | None
    flip_bucket: str
    volatility: str
    zero_dte: bool


def classify_regime(*, spot: float, total_gex: float, gamma_flip: float | None, iv: float | None, zero_dte: bool) -> Regime:
    gamma = "positive" if total_gex > 0 else "negative" if total_gex < 0 else "neutral"
    distance = None if gamma_flip is None else spot - gamma_flip
    if distance is None:
        bucket = "unknown"
    elif abs(distance) <= max(abs(spot) * 0.001, 1.0):
        bucket = "near_flip"
    elif distance > 0:
        bucket = "above_flip"
    else:
        bucket = "below_flip"
    if iv is None:
        volatility = "unknown"
    elif iv < 0.15:
        volatility = "low"
    elif iv < 0.25:
        volatility = "normal"
    else:
        volatility = "high"
    return Regime(gamma, distance, bucket, volatility, zero_dte)
