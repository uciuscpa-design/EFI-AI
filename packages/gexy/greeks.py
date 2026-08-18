from __future__ import annotations

from dataclasses import dataclass, replace
from math import erf, exp, log, pi, sqrt

from packages.gexy.models import OptionSurfacePoint, OptionType


_SQRT_2 = sqrt(2.0)
_SQRT_2PI = sqrt(2.0 * pi)


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / _SQRT_2))


def _norm_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / _SQRT_2PI


@dataclass(frozen=True)
class EuropeanOptionGreeks:
    price: float
    delta: float
    gamma: float
    theta_per_year: float
    vega_per_vol_unit: float
    rho_per_rate_unit: float


@dataclass(frozen=True)
class GreekEnrichment:
    point: OptionSurfacePoint
    source: str
    implied_volatility: float | None


def black_scholes_greeks(
    *,
    option_type: OptionType,
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> EuropeanOptionGreeks:
    """Price a European option and return analytical Black-Scholes Greeks.

    Rates, dividend yield, and volatility are decimal annualized values.
    Theta is per year. Vega and rho are per 1.00 absolute change, not per 1%.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if time_to_expiry_years <= 0:
        raise ValueError("time_to_expiry_years must be positive")
    if volatility <= 0:
        raise ValueError("volatility must be positive")

    sqrt_t = sqrt(time_to_expiry_years)
    sigma_sqrt_t = volatility * sqrt_t
    discount_r = exp(-risk_free_rate * time_to_expiry_years)
    discount_q = exp(-dividend_yield * time_to_expiry_years)
    d1 = (
        log(spot / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility)
        * time_to_expiry_years
    ) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    pdf_d1 = _norm_pdf(d1)

    gamma = discount_q * pdf_d1 / (spot * sigma_sqrt_t)
    vega = spot * discount_q * pdf_d1 * sqrt_t
    common_theta = -(spot * discount_q * pdf_d1 * volatility) / (2.0 * sqrt_t)

    if option_type is OptionType.CALL:
        price = spot * discount_q * _norm_cdf(d1) - strike * discount_r * _norm_cdf(d2)
        delta = discount_q * _norm_cdf(d1)
        theta = (
            common_theta
            - risk_free_rate * strike * discount_r * _norm_cdf(d2)
            + dividend_yield * spot * discount_q * _norm_cdf(d1)
        )
        rho = strike * time_to_expiry_years * discount_r * _norm_cdf(d2)
    else:
        price = strike * discount_r * _norm_cdf(-d2) - spot * discount_q * _norm_cdf(-d1)
        delta = discount_q * (_norm_cdf(d1) - 1.0)
        theta = (
            common_theta
            + risk_free_rate * strike * discount_r * _norm_cdf(-d2)
            - dividend_yield * spot * discount_q * _norm_cdf(-d1)
        )
        rho = -strike * time_to_expiry_years * discount_r * _norm_cdf(-d2)

    return EuropeanOptionGreeks(
        price=price,
        delta=delta,
        gamma=gamma,
        theta_per_year=theta,
        vega_per_vol_unit=vega,
        rho_per_rate_unit=rho,
    )


def implied_volatility_from_price(
    *,
    option_type: OptionType,
    option_price: float,
    spot: float,
    strike: float,
    time_to_expiry_years: float,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
    min_volatility: float = 1e-6,
    max_volatility: float = 5.0,
    tolerance: float = 1e-8,
    max_iterations: int = 120,
) -> float | None:
    """Recover European implied volatility with bounded bisection."""
    if option_price < 0 or spot <= 0 or strike <= 0 or time_to_expiry_years <= 0:
        return None
    if min_volatility <= 0 or max_volatility <= min_volatility:
        raise ValueError("invalid volatility bounds")

    discount_r = exp(-risk_free_rate * time_to_expiry_years)
    discount_q = exp(-dividend_yield * time_to_expiry_years)
    if option_type is OptionType.CALL:
        lower_bound = max(0.0, spot * discount_q - strike * discount_r)
        upper_bound = spot * discount_q
    else:
        lower_bound = max(0.0, strike * discount_r - spot * discount_q)
        upper_bound = strike * discount_r

    if option_price < lower_bound - tolerance or option_price > upper_bound + tolerance:
        return None

    def price_at(volatility: float) -> float:
        return black_scholes_greeks(
            option_type=option_type,
            spot=spot,
            strike=strike,
            time_to_expiry_years=time_to_expiry_years,
            volatility=volatility,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        ).price

    low = min_volatility
    high = max_volatility
    low_price = price_at(low)
    high_price = price_at(high)
    if option_price < low_price - tolerance or option_price > high_price + tolerance:
        return None

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        mid_price = price_at(mid)
        difference = mid_price - option_price
        if abs(difference) <= tolerance:
            return mid
        if difference < 0:
            low = mid
        else:
            high = mid

    return (low + high) / 2.0


def enrich_missing_greeks(
    point: OptionSurfacePoint,
    *,
    spot: float,
    time_to_expiry_years: float,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> GreekEnrichment:
    """Fill missing Greeks from Alpaca IV or quote-implied IV when possible."""
    if point.gamma is not None and point.delta is not None:
        return GreekEnrichment(point=point, source="alpaca", implied_volatility=point.implied_volatility)
    if spot <= 0 or time_to_expiry_years <= 0:
        return GreekEnrichment(point=point, source="unavailable", implied_volatility=point.implied_volatility)

    volatility = point.implied_volatility
    source = "alpaca_iv"
    if volatility is None or volatility <= 0:
        option_price = point.mid
        if option_price is None:
            option_price = point.trade_price
        if option_price is None:
            return GreekEnrichment(point=point, source="unavailable", implied_volatility=None)
        volatility = implied_volatility_from_price(
            option_type=point.option_type,
            option_price=option_price,
            spot=spot,
            strike=point.strike,
            time_to_expiry_years=time_to_expiry_years,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )
        if volatility is None:
            return GreekEnrichment(point=point, source="unavailable", implied_volatility=None)
        source = "quote_implied_iv"

    greeks = black_scholes_greeks(
        option_type=point.option_type,
        spot=spot,
        strike=point.strike,
        time_to_expiry_years=time_to_expiry_years,
        volatility=volatility,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )
    enriched = replace(
        point,
        implied_volatility=volatility,
        delta=point.delta if point.delta is not None else greeks.delta,
        gamma=point.gamma if point.gamma is not None else greeks.gamma,
        theta=point.theta if point.theta is not None else greeks.theta_per_year,
        vega=point.vega if point.vega is not None else greeks.vega_per_vol_unit,
        rho=point.rho if point.rho is not None else greeks.rho_per_rate_unit,
    )
    return GreekEnrichment(point=enriched, source=source, implied_volatility=volatility)
