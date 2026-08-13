from packages.gexy.live_prediction import predict_live
from packages.gexy.surface_features import GEXSurfaceFeatures


def test_positive_gamma_targets_nearest_wall() -> None:
    features = GEXSurfaceFeatures(
        spot=7749.2,
        flip_level=7733.6,
        lower_wall=7740.0,
        upper_wall=7760.0,
        distance_to_flip=15.6,
        distance_to_lower_wall=9.2,
        distance_to_upper_wall=10.8,
        local_gex=168.0,
        local_gex_slope=7.15,
        positive_gamma_regime=True,
        hedge_acceleration=169.9,
    )
    prediction = predict_live(features, horizon_minutes=30)
    assert prediction.direction == "down"
    assert prediction.primary_target == 7740.0
    assert prediction.expected_move_points < 0
    assert prediction.invalidation_level == 7733.6
    assert 0.0 < prediction.confidence <= 0.95
    assert prediction.regime == "positive_gamma_mean_reversion"


def test_negative_gamma_uses_slope_direction() -> None:
    features = GEXSurfaceFeatures(
        spot=7728.0,
        flip_level=7734.0,
        lower_wall=7705.0,
        upper_wall=7740.0,
        distance_to_flip=-6.0,
        distance_to_lower_wall=23.0,
        distance_to_upper_wall=12.0,
        local_gex=-104.0,
        local_gex_slope=-12.0,
        positive_gamma_regime=False,
        hedge_acceleration=-300.0,
    )
    prediction = predict_live(features, horizon_minutes=60)
    assert prediction.direction == "down"
    assert prediction.primary_target == 7705.0
    assert prediction.expected_move_points == -46.0
    assert prediction.regime == "negative_gamma_acceleration"


def test_horizon_must_be_positive() -> None:
    features = GEXSurfaceFeatures(
        spot=100.0,
        flip_level=None,
        lower_wall=None,
        upper_wall=None,
        distance_to_flip=None,
        distance_to_lower_wall=None,
        distance_to_upper_wall=None,
        local_gex=0.0,
        local_gex_slope=0.0,
        positive_gamma_regime=True,
        hedge_acceleration=0.0,
    )
    try:
        predict_live(features, horizon_minutes=0)
    except ValueError as exc:
        assert "horizon_minutes" in str(exc)
    else:
        raise AssertionError("expected ValueError")
