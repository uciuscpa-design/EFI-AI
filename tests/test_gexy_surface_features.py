import pytest

from packages.gexy.surface_features import (
    GEXSurfacePoint,
    build_surface_features,
    estimate_flip_level,
)


def test_estimate_flip_level_interpolates_zero_crossing() -> None:
    points = (
        GEXSurfacePoint(7730, -104.0),
        GEXSurfacePoint(7735, -10.0),
        GEXSurfacePoint(7740, 183.0),
    )
    flip = estimate_flip_level(points)
    assert flip is not None
    assert 7735 < flip < 7740


def test_build_surface_features_finds_walls_and_regime() -> None:
    points = (
        GEXSurfacePoint(7705, -82.0),
        GEXSurfacePoint(7720, -67.0),
        GEXSurfacePoint(7730, -104.0),
        GEXSurfacePoint(7740, 183.0),
        GEXSurfacePoint(7750, 168.0),
        GEXSurfacePoint(7760, 326.0),
        GEXSurfacePoint(7775, 281.0),
        GEXSurfacePoint(7800, 299.0),
    )
    features = build_surface_features(points, spot=7749.2)

    assert features.flip_level is not None
    assert 7730 < features.flip_level < 7740
    assert features.lower_wall == 7740
    assert features.upper_wall == 7760
    assert features.distance_to_flip is not None
    assert features.distance_to_flip > 0
    assert features.distance_to_lower_wall == pytest.approx(9.2)
    assert features.distance_to_upper_wall == pytest.approx(10.8)
    assert features.local_gex == 168.0
    assert features.positive_gamma_regime is True
    assert features.hedge_acceleration != 0
