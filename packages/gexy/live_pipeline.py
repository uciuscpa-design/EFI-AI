from __future__ import annotations

from dataclasses import dataclass

from .gax_features import GAXFeatures, build_gax_features
from .live_prediction import LivePrediction, predict_live
from .market_adapter import MarketSnapshot
from .multi_horizon import DEFAULT_HORIZONS, MultiHorizonPrediction, predict_multi_horizon
from .option_surface import aggregate_surface
from .surface_features import GEXSurfaceFeatures, GEXSurfacePoint, build_surface_features


@dataclass(frozen=True)
class LivePipelineResult:
    snapshot: MarketSnapshot
    surface_features: GEXSurfaceFeatures
    gax_features: GAXFeatures
    prediction: LivePrediction
    multi_horizon: MultiHorizonPrediction


def surface_points_from_snapshot(snapshot: MarketSnapshot) -> tuple[GEXSurfacePoint, ...]:
    """Collapse the normalized option snapshot into signed GEX by strike."""
    surface = aggregate_surface(snapshot.options)
    if not surface.strikes:
        raise ValueError("snapshot must contain at least one option observation")
    return tuple(
        GEXSurfacePoint(strike=point.strike, signed_gex=point.gex)
        for point in surface.strikes
    )


def run_live_pipeline(
    snapshot: MarketSnapshot,
    *,
    horizon_minutes: int = 30,
) -> LivePipelineResult:
    """Produce GEX/GAX features plus single- and multi-horizon forecasts.

    ``prediction`` remains the requested single-horizon result for backward
    compatibility. ``multi_horizon`` evaluates the standard 5/15/30/60 minute
    windows from the exact same surface; a custom requested horizon is added if
    it is not already present in that standard bundle. ``gax_features`` is an
    explicitly labeled GEX-spatial-derivative proxy, not direct dealer-position
    GAX data.
    """
    points = surface_points_from_snapshot(snapshot)
    features = build_surface_features(points, spot=snapshot.spot)
    gax_features = build_gax_features(points, spot=snapshot.spot)
    prediction = predict_live(features, horizon_minutes=horizon_minutes)
    horizons = DEFAULT_HORIZONS
    if horizon_minutes not in horizons:
        horizons = (*horizons, horizon_minutes)
    multi_horizon = predict_multi_horizon(features, horizons=horizons)
    return LivePipelineResult(
        snapshot=snapshot,
        surface_features=features,
        gax_features=gax_features,
        prediction=prediction,
        multi_horizon=multi_horizon,
    )
