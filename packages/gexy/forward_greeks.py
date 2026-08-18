from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt
from statistics import median

from packages.gexy.models import OptionType


_SQRT_2 = sqrt(2.0)
_SQRT_2PI = sqrt(2.0 * pi)


def _norm_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / _SQRT_2))


def _norm_pdf(value: float) -> float:
    return exp(-0.5 * value * value) / _SQRT_2PI


@dataclass(frozen=True)
class ParityForwardFit:
    forward: float
    discount_factor: float
    pair_count: int
    max_abs_residual: float
    median_abs_residual: float


@dataclass(frozen=True)
class ForwardOptionGreeks:
    price: float
    delta_forward: float
    gamma_forward: float
    vega_per_vol_unit: float


def fit_forward_discount_from_parity(
    pairs: list[tuple[float, float, float]],
) -> ParityForwardFit:
    """Robustly fit C-P = D * (F-K) across matched European option pairs.

    Each tuple is ``(strike, call_mid, put_mid)``.  The slope of ``C-P`` versus
    strike is ``-D`` and the intercept is ``D*F``.  A Theil-Sen style median
    slope is used so a handful of stale/wide quotes do not dominate the fit.
    """
    clean = [
        (float(strike), float(call), float(put))
        for strike, call, put in pairs
        if strike > 0 and call >= 0 and put >= 0
    ]
    if len(clean) < 2:
        raise ValueError("at least two matched call/put strikes are required")

    xy = [(strike, call - put) for strike, call, put in clean]
    slopes: list[float] = []
    for index, (strike_a, value_a) in enumerate(xy):
        for strike_b, value_b in xy[index + 1 :]:
            delta_strike = strike_b - strike_a
            if delta_strike != 0:
                slopes.append((value_b - value_a) / delta_strike)
    if not slopes:
        raise ValueError("matched pairs must contain at least two distinct strikes")

    discount_factor = -median(slopes)
    if not 0.5 <= discount_factor <= 1.5:
        raise ValueError(
            f"put-call parity implied an implausible discount factor: {discount_factor:.6f}"
        )

    intercept = median(value + discount_factor * strike for strike, value in xy)
    forward = intercept / discount_factor
    if forward <= 0:
        raise ValueError("put-call parity implied a non-positive forward")

    residuals = [
        abs(value - discount_factor * (forward - strike)) for strike, value in xy
    ]
    return ParityForwardFit(
        forward=forward,
        discount_factor=discount_factor,
        pair_count=len(clean),
        max_abs_residual=max(residuals),
        median_abs_residual=median(residuals),
    )


def black76_greeks(
    *,
    option_type: OptionType,
    forward: float,
    strike: float,
    time_to_expiry_years: float,
    volatility: float,
    discount_factor: float = 1.0,
) -> ForwardOptionGreeks:
    """Return Black-76 price and Greeks with respect to the forward.

    ``gamma_forward`` is d(delta_forward)/dF.  GEXY uses it as a short-dated
    SPX hedge-curvature proxy and keeps that interpretation explicit rather
    than claiming it is an observed dealer spot gamma.
    """
    if forward <= 0:
        raise ValueError("forward must be positive")
    if strike <= 0:
        raise ValueError("strike must be positive")
    if time_to_expiry_years <= 0:
        raise ValueError("time_to_expiry_years must be positive")
    if volatility <= 0:
        raise ValueError("volatility must be positive")
    if discount_factor <= 0:
        raise ValueError("discount_factor must be positive")

    sqrt_t = sqrt(time_to_expiry_years)
    sigma_sqrt_t = volatility * sqrt_t
    d1 = (log(forward / strike) + 0.5 * volatility * volatility * time_to_expiry_years) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    pdf_d1 = _norm_pdf(d1)

    gamma_forward = discount_factor * pdf_d1 / (forward * sigma_sqrt_t)
    vega = discount_factor * forward * pdf_d1 * sqrt_t

    if option_type is OptionType.CALL:
        price = discount_factor * (
            forward * _norm_cdf(d1) - strike * _norm_cdf(d2)
        )
        delta_forward = discount_factor * _norm_cdf(d1)
    else:
        price = discount_factor * (
            strike * _norm_cdf(-d2) - forward * _norm_cdf(-d1)
        )
        delta_forward = -discount_factor * _norm_cdf(-d1)

    return ForwardOptionGreeks(
        price=price,
        delta_forward=delta_forward,
        gamma_forward=gamma_forward,
        vega_per_vol_unit=vega,
    )


def implied_volatility_from_forward_price(
    *,
    option_type: OptionType,
    option_price: float,
    forward: float,
    strike: float,
    time_to_expiry_years: float,
    discount_factor: float = 1.0,
    min_volatility: float = 1e-6,
    max_volatility: float = 5.0,
    tolerance: float = 1e-8,
    max_iterations: int = 120,
) -> float | None:
    """Recover Black-76 implied volatility with bounded bisection."""
    if (
        option_price < 0
        or forward <= 0
        or strike <= 0
        or time_to_expiry_years <= 0
        or discount_factor <= 0
    ):
        return None
    if min_volatility <= 0 or max_volatility <= min_volatility:
        raise ValueError("invalid volatility bounds")

    if option_type is OptionType.CALL:
        lower_bound = discount_factor * max(0.0, forward - strike)
        upper_bound = discount_factor * forward
    else:
        lower_bound = discount_factor * max(0.0, strike - forward)
        upper_bound = discount_factor * strike

    if option_price < lower_bound - tolerance or option_price > upper_bound + tolerance:
        return None

    def price_at(volatility: float) -> float:
        return black76_greeks(
            option_type=option_type,
            forward=forward,
            strike=strike,
            time_to_expiry_years=time_to_expiry_years,
            volatility=volatility,
            discount_factor=discount_factor,
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
