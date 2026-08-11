from packages.gexy.engine import GexyEngine
from packages.gexy.models import GexyOption, GexyScenario


def _option(option_type: str, strike: float, oi: float = 1000) -> GexyOption:
    return GexyOption(
        symbol=f"SPX-{strike}-{option_type}",
        strike=strike,
        option_type=option_type,
        expiration="2026-08-21",
        open_interest=oi,
        iv=0.20,
        days_to_expiry=10,
    )


def test_gamma_is_positive_for_valid_option():
    engine = GexyEngine()
    surface = engine.surface([_option("call", 7700)], 7700, GexyScenario.DEALER_LONG_GAMMA, steps=5)
    assert surface.points
    assert any(point.net_gex > 0 for point in surface.points)


def test_short_gamma_reverses_exposure_sign():
    engine = GexyEngine()
    options = [_option("call", 7700), _option("put", 7700)]
    long = engine.surface(options, 7700, GexyScenario.DEALER_LONG_GAMMA, steps=5)
    short = engine.surface(options, 7700, GexyScenario.DEALER_SHORT_GAMMA, steps=5)
    assert long.points[2].net_gex == -short.points[2].net_gex


def test_missing_iv_and_quote_reduces_quality():
    engine = GexyEngine()
    bad = _option("call", 7700)
    bad.iv = None
    bad.mid = None
    bad.days_to_expiry = None
    surface = engine.surface([bad], 7700, GexyScenario.DEALER_LONG_GAMMA, steps=3)
    assert surface.data_quality == 0
    assert surface.prediction_available is False
