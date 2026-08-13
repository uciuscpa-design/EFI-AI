from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class GEXSurfacePoint:
    strike: float
    signed_gex: float


@dataclass(frozen=True)
class GEXSurfaceFeatures:
    spot: float
    flip_level: float | None
    lower_wall: float | None
    upper_wall: float | None
    distance_to_flip: float | None
    distance_to_lower_wall: float | None
    distance_to_upper_wall: float | None
    local_gex: float
    local_gex_slope: float
    positive_gamma_regime: bool
    hedge_acceleration: float


def _ordered(points: Sequence[GEXSurfacePoint]) -> tuple[GEXSurfacePoint, ...]:
    if not points:
        raise ValueError("points must not be empty")
    ordered = tuple(sorted(points, key=lambda point: point.strike))
    if any(point.strike <= 0 for point in ordered):
        raise ValueError("strikes must be positive")
    if any(ordered[i].strike == ordered[i - 1].strike for i in range(1, len(ordered))):
        raise ValueError("strikes must be unique")
    return ordered


def estimate_flip_level(points: Sequence[GEXSurfacePoint]) -> float | None:
    """Linearly interpolate the nearest strike where signed GEX crosses zero."""
    ordered = _ordered(points)
    candidates: list[float] = []
    for left, right in zip(ordered, ordered[1:]):
        if left.signed_gex == 0:
            candidates.append(left.strike)
            continue
        if right.signed_gex == 0:
            candidates.append(right.strike)
            continue
        if left.signed_gex * right.signed_gex < 0:
            span = right.strike - left.strike
            weight = abs(left.signed_gex) / (abs(left.signed_gex) + abs(right.signed_gex))
            candidates.append(left.strike + span * weight)
    if not candidates:
        return None
    center = (ordered[0].strike + ordered[-1].strike) / 2.0
    return min(candidates, key=lambda level: abs(level - center))


def _nearest_index(points: Sequence[GEXSurfacePoint], spot: float) -> int:
    return min(range(len(points)), key=lambda index: abs(points[index].strike - spot))


def build_surface_features(
    points: Sequence[GEXSurfacePoint],
    *,
    spot: float,
) -> GEXSurfaceFeatures:
    """Convert a signed-GEX strike curve into live prediction features.

    Walls are the strongest absolute GEX concentrations strictly below/above
    spot. Local slope is dGEX/dStrike around the nearest strike. Hedge
    acceleration is a normalized slope proxy: large magnitude means hedging
    pressure changes rapidly as spot moves across nearby strikes.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    ordered = _ordered(points)
    index = _nearest_index(ordered, spot)
    local = ordered[index]

    lower = [point for point in ordered if point.strike < spot]
    upper = [point for point in ordered if point.strike > spot]
    lower_wall = max(lower, key=lambda point: abs(point.signed_gex)).strike if lower else None
    upper_wall = max(upper, key=lambda point: abs(point.signed_gex)).strike if upper else None

    if len(ordered) == 1:
        slope = 0.0
    elif index == 0:
        right = ordered[1]
        slope = (right.signed_gex - local.signed_gex) / (right.strike - local.strike)
    elif index == len(ordered) - 1:
        left = ordered[-2]
        slope = (local.signed_gex - left.signed_gex) / (local.strike - left.strike)
    else:
        left = ordered[index - 1]
        right = ordered[index + 1]
        slope = (right.signed_gex - left.signed_gex) / (right.strike - left.strike)

    flip = estimate_flip_level(ordered)
    scale = max(abs(point.signed_gex) for point in ordered) or 1.0
    hedge_acceleration = slope * spot / scale

    return GEXSurfaceFeatures(
        spot=float(spot),
        flip_level=flip,
        lower_wall=lower_wall,
        upper_wall=upper_wall,
        distance_to_flip=None if flip is None else spot - flip,
        distance_to_lower_wall=None if lower_wall is None else spot - lower_wall,
        distance_to_upper_wall=None if upper_wall is None else upper_wall - spot,
        local_gex=local.signed_gex,
        local_gex_slope=slope,
        positive_gamma_regime=local.signed_gex >= 0,
        hedge_acceleration=hedge_acceleration,
    )
