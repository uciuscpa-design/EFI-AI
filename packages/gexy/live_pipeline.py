from __future__ import annotations

from dataclasses import dataclass

from .live_prediction import LivePrediction, predict_live
from .market_adapter import MarketSnapshot
from .option_surface import aggregate_surface
from .surface_features import GEXSurfaceFeatures, GEXSurfacePoint, build_surface_features


@dataclass(frozen=True)
class LivePipelineResult:
    snapshot: MarketSnapshot
    surface_features: GEXSurfaceFeatures
    prediction: LivePrediction


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
    """Produce a deterministic live forecast from one normalized market snapshot.

    The caller owns data acquisition and sign normalization. This keeps the core
    prediction path independent of Alpaca while allowing AlpacaSpxSnapshotProvider
    (or any future provider) to feed the exact same pipeline.
    """
    points = surface_points_from_snapshot(snapshot)
    features = build_surface_features(points, spot=snapshot.spot)
    prediction = predict_live(features, horizon_minutes=horizon_minutes)
    return LivePipelineResult(snapshot, features, prediction)
