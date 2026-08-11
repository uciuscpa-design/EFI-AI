from packages.gexy.hedge_pressure import estimate_hedge_pressure


def test_pressure_is_transparent_and_finite() -> None:
    pressure = estimate_hedge_pressure(
        total_gex=10,
        total_vanna=4,
        total_charm=2,
        spot_change=1,
        iv_change=0.05,
    )
    assert pressure.gamma_pressure == 10
    assert pressure.vanna_pressure == 0.2
    assert pressure.charm_pressure == 2
    assert pressure.total_pressure == 12.2
    assert 0 <= pressure.confidence <= 1
