from __future__ import annotations

import math
from dataclasses import dataclass

from .models import GexyOption, GexyPoint, GexyScenario, GexySurface

SQRT_2PI = math.sqrt(2 * math.pi)


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_price(spot: float, strike: float, t: float, vol: float, rate: float, call: bool) -> float:
    if t <= 0:
        return max(spot - strike, 0.0) if call else max(strike - spot, 0.0)
    if vol <= 0:
        return max(spot - strike, 0.0) if call else max(strike - spot, 0.0)
    root_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * t) / (vol * root_t)
    d2 = d1 - vol * root_t
    disc = math.exp(-rate * t)
    if call:
        return spot * _norm_cdf(d1) - strike * disc * _norm_cdf(d2)
    return strike * disc * _norm_cdf(-d2) - spot * _norm_cdf(-d1)


def implied_volatility(price: float, spot: float, strike: float, t: float, rate: float = 0.0, call: bool = True) -> float | None:
    if price <= 0 or spot <= 0 or strike <= 0 or t <= 0:
        return None
    intrinsic = max(spot - strike, 0.0) if call else max(strike - spot, 0.0)
    if price < intrinsic - 1e-8:
        return None
    lo, hi = 1e-6, 5.0
    for _ in range(80):
        mid = (lo + hi) / 2
        value = _bs_price(spot, strike, t, mid, rate, call)
        if value > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def gamma(spot: float, strike: float, t: float, vol: float, rate: float = 0.0) -> float:
    if min(spot, strike, t, vol) <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * t) / (vol * math.sqrt(t))
    return _norm_pdf(d1) / (spot * vol * math.sqrt(t))


@dataclass(frozen=True)
class _Exposure:
    gex: float
    call_gex: float
    put_gex: float


class GexyEngine:
    """Deterministic GEX calculation with explicit positioning scenarios.

    GEX is stored in index-dollar units using the common 1% convention:
    gamma * OI * multiplier * spot^2 * 0.01. Dealer hedge response is
    represented as -GEX * dS, so positive dealer gamma hedges against a move
    while negative dealer gamma reinforces it.
    """

    def __init__(self, risk_free_rate: float = 0.0):
        self.risk_free_rate = risk_free_rate

    def _iv(self, option: GexyOption, spot: float) -> float | None:
        if option.iv:
            return option.iv
        price = option.mid
        if price is None and option.bid is not None and option.ask is not None:
            price = (option.bid + option.ask) / 2
        if price is None or option.days_to_expiry is None:
            return None
        return implied_volatility(
            price,
            spot,
            option.strike,
            option.days_to_expiry / 365.0,
            self.risk_free_rate,
            option.option_type == "call",
        )

    def _exposure(self, options: list[GexyOption], spot: float, scenario: GexyScenario) -> _Exposure:
        call = put = 0.0
        for option in options:
            t = (option.days_to_expiry or 0.0) / 365.0
            vol = self._iv(option, spot)
            if not vol:
                continue
            g = gamma(spot, option.strike, t, vol, self.risk_free_rate)
            magnitude = g * option.open_interest * option.multiplier * spot * spot * 0.01 * option.oi_confidence
            if option.option_type == "call":
                call += magnitude
            else:
                put += magnitude
        if scenario == GexyScenario.DEALER_LONG_GAMMA:
            return _Exposure(call + put, call, put)
        if scenario == GexyScenario.DEALER_SHORT_GAMMA:
            return _Exposure(-(call + put), -call, -put)
        # Mixed is intentionally neutral until an inventory model is supplied.
        return _Exposure(0.0, 0.0, 0.0)

    def surface(self, options: list[GexyOption], reference_price: float, scenario: GexyScenario, pct_range: float = 0.02, steps: int = 81) -> GexySurface:
        if not options or reference_price <= 0:
            return GexySurface(reference_price=reference_price, scenario=scenario, points=[], data_quality=0.0, reason="No valid options or reference price")
        lo = reference_price * (1 - pct_range)
        hi = reference_price * (1 + pct_range)
        spots = [lo + (hi - lo) * i / max(1, steps - 1) for i in range(steps)]
        points: list[GexyPoint] = []
        for spot in spots:
            e = self._exposure(options, spot, scenario)
            points.append(GexyPoint(spot=spot, net_gex=e.gex, hedge_pressure_per_1pct=-e.gex * spot * 0.01, call_gex=e.call_gex, put_gex=e.put_gex))

        flip = None
        for a, b in zip(points, points[1:]):
            if a.net_gex == 0:
                flip = a.spot
                break
            if a.net_gex * b.net_gex < 0:
                weight = abs(a.net_gex) / (abs(a.net_gex) + abs(b.net_gex))
                flip = a.spot + (b.spot - a.spot) * weight
                break

        by_call = max(points, key=lambda p: abs(p.call_gex), default=None)
        by_put = max(points, key=lambda p: abs(p.put_gex), default=None)
        quality = sum(1 for o in options if self._iv(o, reference_price) is not None) / len(options)
        return GexySurface(
            reference_price=reference_price,
            scenario=scenario,
            points=points,
            gamma_flip=flip,
            call_wall=by_call.spot if by_call else None,
            put_wall=by_put.spot if by_put else None,
            data_quality=quality,
            prediction_available=False,
            reason="Exposure surface only; no historical model calibration supplied",
        )
