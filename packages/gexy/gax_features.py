from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .surface_features import GEXSurfacePoint


@dataclass(frozen=True)
class GAXFeatures:
    """Project-specific gamma-acceleration proxy derived from the GEX strike curve.

    This is not a claim of direct dealer-position GAX. It is a transparent
    spatial proxy based on how signed GEX changes around current spot.
    """

    spot: float
    local_gax: float
    local_gax_curvature: float
    magnitude: float
    acceleration_bias: str
    source: str = "gex_spatial_derivative_proxy_v1"


def _ordered(points: Sequence[GEXSurfacePoint]) -> tuple[GEXSurfacePoint, ...]:
    if not points:
        raise ValueError("points must not be empty")
    ordered = tuple(sorted(points, key=lambda point: point.strike))
    if any(point.strike <= 0 for point in ordered):
        raise ValueError("strikes must be positive")
    if any(ordered[i].strike == ordered[i - 1].strike for i in range(1, len(ordered))):
        raise ValueError("strikes must be unique")
    return ordered


def _nearest_index(points: Sequence[GEXSurfacePoint], spot: float) -> int:
    return min(range(len(points)), key=lambda index: abs(points[index].strike - spot))


def _slope(left: GEXSurfacePoint, right: GEXSurfacePoint) -> float:
    return (right.signed_gex - left.signed_gex) / (right.strike - left.strike)


def build_gax_features(
    points: Sequence[GEXSurfacePoint],
    *,
    spot: float,
) -> GAXFeatures:
    if spot <= 0:
        raise ValueError("spot must be positive")

    ordered = _ordered(points)
    index = _nearest_index(ordered, spot)
    scale = max(abs(point.signed_gex) for point in ordered) or 1.0

    if len(ordered) == 1:
        local_slope = 0.0
        curvature = 0.0
    elif index == 0:
        local_slope = _slope(ordered[0], ordered[1])
        if len(ordered) >= 3:
            slope_right = _slope(ordered[1], ordered[2])
            midpoint_span = (ordered[2].strike - ordered[0].strike) / 2.0
            curvature = (slope_right - local_slope) / midpoint_span
        else:
            curvature = 0.0
    elif index == len(ordered) - 1:
        local_slope = _slope(ordered[-2], ordered[-1])
        if len(ordered) >= 3:
            slope_left = _slope(ordered[-3], ordered[-2])
            midpoint_span = (ordered[-1].strike - ordered[-3].strike) / 2.0
            curvature = (local_slope - slope_left) / midpoint_span
        else:
            curvature = 0.0
    else:
        left = ordered[index - 1]
        center = ordered[index]
        right = ordered[index + 1]
        slope_left = _slope(left, center)
        slope_right = _slope(center, right)
        local_slope = (right.signed_gex - left.signed_gex) / (right.strike - left.strike)
        midpoint_span = (right.strike - left.strike) / 2.0
        curvature = (slope_right - slope_left) / midpoint_span

    local_gax = local_slope * spot / scale
    normalized_curvature = curvature * spot * spot / scale
    magnitude = abs(local_gax)
    if local_gax > 1e-12:
        bias = "up"
    elif local_gax < -1e-12:
        bias = "down"
    else:
        bias = "neutral"

    return GAXFeatures(
        spot=float(spot),
        local_gax=float(local_gax),
        local_gax_curvature=float(normalized_curvature),
        magnitude=float(magnitude),
        acceleration_bias=bias,
    )
