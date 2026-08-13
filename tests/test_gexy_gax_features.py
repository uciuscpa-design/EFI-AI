import pytest

from packages.gexy.gax_features import build_gax_features
from packages.gexy.surface_features import GEXSurfacePoint, build_surface_features


def test_gax_proxy_tracks_local_gex_slope() -> None:
    points = (
        GEXSurfacePoint(7730, -100.0),
        GEXSurfacePoint(7740, 0.0),
        GEXSurfacePoint(7750, 100.0),
    )
    features = build_gax_features(points, spot=7742.0)
    assert features.local_gax > 0
    assert features.acceleration_bias == "up"
    assert features.local_gax_curvature == 0.0
    assert features.source == "gex_spatial_derivative_proxy_v1"


def test_gax_proxy_detects_curvature() -> None:
    points = (
        GEXSurfacePoint(7730, -100.0),
        GEXSurfacePoint(7740, -50.0),
        GEXSurfacePoint(7750, 100.0),
    )
    features = build_gax_features(points, spot=7740.0)
    assert features.local_gax > 0
    assert features.local_gax_curvature > 0
    assert features.magnitude == abs(features.local_gax)


def test_gax_proxy_neutral_for_flat_curve() -> None:
    points = (
        GEXSurfacePoint(7730, 25.0),
        GEXSurfacePoint(7740, 25.0),
        GEXSurfacePoint(7750, 25.0),
    )
    features = build_gax_features(points, spot=7740.0)
    assert features.local_gax == 0.0
    assert features.local_gax_curvature == 0.0
    assert features.acceleration_bias == "neutral"


def test_gax_v1_matches_legacy_hedge_acceleration_without_double_counting() -> None:
    points = (
        GEXSurfacePoint(7730, -104.0),
        GEXSurfacePoint(7740, 183.0),
        GEXSurfacePoint(7750, 168.0),
        GEXSurfacePoint(7760, 326.0),
    )
    spot = 7749.2
    gax = build_gax_features(points, spot=spot)
    gex = build_surface_features(points, spot=spot)
    assert gax.local_gax == pytest.approx(gex.hedge_acceleration)
