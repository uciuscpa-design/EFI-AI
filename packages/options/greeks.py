from math import erf, exp, log, pi, sqrt

from packages.options.models import OptionType

_SQRT_2PI = sqrt(2 * pi)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / _SQRT_2PI


def _validate_inputs(spot: float, strike: float, years_to_expiry: float, volatility: float) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if years_to_expiry <= 0:
        raise ValueError("years_to_expiry must be positive")
    if volatility <= 0:
        raise ValueError("volatility must be positive")


def black_scholes_price(
    *,
    spot: float,
    strike: float,
    years_to_expiry: float,
    volatility: float,
    option_type: OptionType,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> float:
    """European Black-Scholes price with a continuous dividend yield."""
    _validate_inputs(spot, strike, years_to_expiry, volatility)
    root_t = sqrt(years_to_expiry)
    d1 = (
        log(spot / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility) * years_to_expiry
    ) / (volatility * root_t)
    d2 = d1 - volatility * root_t
    discounted_spot = spot * exp(-dividend_yield * years_to_expiry)
    discounted_strike = strike * exp(-risk_free_rate * years_to_expiry)

    if option_type is OptionType.CALL:
        return discounted_spot * _normal_cdf(d1) - discounted_strike * _normal_cdf(d2)
    if option_type is OptionType.PUT:
        return discounted_strike * _normal_cdf(-d2) - discounted_spot * _normal_cdf(-d1)
    raise ValueError(f"unsupported option_type: {option_type}")


def black_scholes_gamma(
    *,
    spot: float,
    strike: float,
    years_to_expiry: float,
    volatility: float,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> float:
    """European spot gamma; calls and puts have the same gamma for equal inputs."""
    _validate_inputs(spot, strike, years_to_expiry, volatility)
    root_t = sqrt(years_to_expiry)
    d1 = (
        log(spot / strike)
        + (risk_free_rate - dividend_yield + 0.5 * volatility * volatility) * years_to_expiry
    ) / (volatility * root_t)
    return exp(-dividend_yield * years_to_expiry) * _normal_pdf(d1) / (spot * volatility * root_t)


def implied_volatility(
    *,
    market_price: float,
    spot: float,
    strike: float,
    years_to_expiry: float,
    option_type: OptionType,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
    tolerance: float = 1e-7,
    max_iterations: int = 200,
) -> float:
    """Solve European implied volatility with a bounded bisection search."""
    if market_price < 0:
        raise ValueError("market_price cannot be negative")
    if spot <= 0 or strike <= 0 or years_to_expiry <= 0:
        raise ValueError("spot, strike, and years_to_expiry must be positive")

    discounted_spot = spot * exp(-dividend_yield * years_to_expiry)
    discounted_strike = strike * exp(-risk_free_rate * years_to_expiry)
    if option_type is OptionType.CALL:
        lower_bound = max(0.0, discounted_spot - discounted_strike)
        upper_bound = discounted_spot
    elif option_type is OptionType.PUT:
        lower_bound = max(0.0, discounted_strike - discounted_spot)
        upper_bound = discounted_strike
    else:
        raise ValueError(f"unsupported option_type: {option_type}")

    epsilon = max(tolerance, 1e-12)
    if market_price < lower_bound - epsilon or market_price > upper_bound + epsilon:
        raise ValueError("market_price violates European no-arbitrage bounds")
    if abs(market_price - lower_bound) <= epsilon:
        return 0.0

    low = 1e-6
    high = 5.0
    high_price = black_scholes_price(
        spot=spot,
        strike=strike,
        years_to_expiry=years_to_expiry,
        volatility=high,
        option_type=option_type,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )
    while high_price < market_price and high < 20.0:
        high *= 2.0
        high_price = black_scholes_price(
            spot=spot,
            strike=strike,
            years_to_expiry=years_to_expiry,
            volatility=high,
            option_type=option_type,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )
    if high_price < market_price:
        raise ValueError("unable to bracket implied volatility")

    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        model_price = black_scholes_price(
            spot=spot,
            strike=strike,
            years_to_expiry=years_to_expiry,
            volatility=mid,
            option_type=option_type,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )
        error = model_price - market_price
        if abs(error) <= tolerance:
            return mid
        if error > 0:
            high = mid
        else:
            low = mid

    return (low + high) / 2.0
