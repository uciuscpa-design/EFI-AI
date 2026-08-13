from __future__ import annotations

from dataclasses import dataclass
from math import exp

from .surface_features import GEXSurfaceFeatures


@dataclass(frozen=True)
class LivePrediction:
    direction: str
    expected_move_points: float
    primary_target: float | None
    invalidation_level: float | None
    confidence: float
    horizon_minutes: int
    regime: str


def _confidence(features: GEXSurfaceFeatures, expected_move: float) -> float:
    wall_distance = min(
        value
        for value in (
            features.distance_to_lower_wall,
            features.distance_to_upper_wall,
        )
        if value is not None
    ) if any(value is not None for value in (features.distance_to_lower_wall, features.distance_to_upper_wall)) else 25.0
    flip_distance = abs(features.distance_to_flip) if features.distance_to_flip is not None else 25.0
    structure = abs(features.local_gex_slope) + abs(features.hedge_acceleration) / 10.0
    raw = structure / max(wall_distance + flip_distance + abs(expected_move), 1.0)
    return max(0.05, min(0.95, 1.0 - exp(-raw)))


def predict_live(
    features: GEXSurfaceFeatures,
    *,
    horizon_minutes: int = 30,
) -> LivePrediction:
    """Convert live GEX surface features into a deterministic first-pass forecast.

    This is intentionally transparent rather than ML-trained. In positive gamma,
    the nearest strong wall acts as the primary mean-reversion target. In negative
    gamma, the model projects away from the flip and toward the nearest wall in the
    direction implied by the local GEX slope. The move estimate is capped by the
    nearest relevant structural level and scaled by the requested horizon.
    """
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")

    horizon_scale = max(0.25, min(2.0, horizon_minutes / 30.0))

    if features.positive_gamma_regime:
        candidates = [
            level
            for level in (features.lower_wall, features.upper_wall)
            if level is not None
        ]
        target = min(candidates, key=lambda level: abs(level - features.spot)) if candidates else features.flip_level
        if target is None:
            direction = "flat"
            expected_move = 0.0
        else:
            delta = target - features.spot
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
            expected_move = delta * min(1.0, horizon_scale)
        regime = "positive_gamma_mean_reversion"
    else:
        if features.local_gex_slope < 0:
            target = features.lower_wall
        elif features.local_gex_slope > 0:
            target = features.upper_wall
        else:
            target = features.flip_level
        if target is None:
            direction = "flat"
            expected_move = 0.0
        else:
            delta = target - features.spot
            direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
            expected_move = delta * horizon_scale
        regime = "negative_gamma_acceleration"

    confidence = _confidence(features, expected_move)
    return LivePrediction(
        direction=direction,
        expected_move_points=float(expected_move),
        primary_target=target,
        invalidation_level=features.flip_level,
        confidence=confidence,
        horizon_minutes=horizon_minutes,
        regime=regime,
    )
