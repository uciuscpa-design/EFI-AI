from datetime import date

import pytest

from packages.options.analytics import GammaSource, derive_option_analytics
from packages.options.greeks import black_scholes_gamma, black_scholes_price
from packages.options.models import OptionContract, OptionGreeks, OptionSnapshot, OptionStyle, OptionType


def _contract() -> OptionContract:
    return OptionContract(
        symbol="SPXW260817C07800000",
        underlying_symbol="SPX",
        root_symbol="SPXW",
        expiration_date=date(2026, 8, 17),
        strike_price=7800.0,
        option_type=OptionType.CALL,
        style=OptionStyle.EUROPEAN,
        multiplier=100.0,
        open_interest=1444.0,
        open_interest_date=date(2026, 8, 12),
    )


def test_derive_uses_feed_gamma_first() -> None:
    snapshot = OptionSnapshot(
        symbol=_contract().symbol,
        bid=8.0,
        ask=8.2,
        implied_volatility=None,
        greeks=OptionGreeks(gamma=0.0123),
    )
    result = derive_option_analytics(
        contract=_contract(),
        snapshot=snapshot,
        spot=7785.0,
        years_to_expiry=3 / 365,
    )
    assert result.gamma == pytest.approx(0.0123)
    assert result.implied_volatility is None
    assert result.gamma_source is GammaSource.FEED_GAMMA


def test_derive_calculates_gamma_from_feed_iv() -> None:
    snapshot = OptionSnapshot(
        symbol=_contract().symbol,
        bid=8.0,
        ask=8.2,
        implied_volatility=0.18,
    )
    result = derive_option_analytics(
        contract=_contract(),
        snapshot=snapshot,
        spot=7785.0,
        years_to_expiry=3 / 365,
        risk_free_rate=0.04,
    )
    expected = black_scholes_gamma(
        spot=7785.0,
        strike=7800.0,
        years_to_expiry=3 / 365,
        volatility=0.18,
        risk_free_rate=0.04,
    )
    assert result.gamma == pytest.approx(expected)
    assert result.gamma_source is GammaSource.FEED_IV


def test_derive_solves_iv_and_gamma_from_mark() -> None:
    spot = 7785.0
    years = 3 / 365
    expected_iv = 0.20
    price = black_scholes_price(
        spot=spot,
        strike=7800.0,
        years_to_expiry=years,
        volatility=expected_iv,
        option_type=OptionType.CALL,
        risk_free_rate=0.04,
    )
    snapshot = OptionSnapshot(symbol=_contract().symbol, bid=price - 0.01, ask=price + 0.01)
    result = derive_option_analytics(
        contract=_contract(),
        snapshot=snapshot,
        spot=spot,
        years_to_expiry=years,
        risk_free_rate=0.04,
    )
    assert result.implied_volatility == pytest.approx(expected_iv, abs=1e-6)
    assert result.gamma > 0
    assert result.gamma_source is GammaSource.SOLVED_IV
