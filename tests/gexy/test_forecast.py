from packages.gexy.forecast import forecast_from_pressure
from packages.gexy.models import HedgePressure


def test_forecast_probabilities_sum_to_one() -> None:
    pressure = HedgePressure(
        spot=6500,
        gamma_component=1,
        vanna_component=0,
        charm_component=0,
        total_delta_change=-2,
        estimated_hedge_demand=2,
        direction="buy",
        confidence=0.5,
    )
    result = forecast_from_pressure(
        pressure,
        horizon_minutes=5,
        realized_vol_points_per_sqrt_minute=2,
    )
    assert 0 <= result.direction_up_probability <= 1
    assert 0 <= result.direction_down_probability <= 1
    assert abs(result.direction_up_probability + result.direction_down_probability - 1) < 1e-12
