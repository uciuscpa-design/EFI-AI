from __future__ import annotations

from .models import HedgePressure, OptionContract


def estimate_hedge_pressure(
    options: list[OptionContract],
    spot: float,
    price_change: float,
    iv_change: float = 0.0,
    elapsed_years: float = 0.0,
) -> HedgePressure:
    """Estimate dealer hedge demand for a small scenario move.

    dDealerDelta ~= Gamma*dS + Vanna*dIV + Charm*dt.
    Hedge demand is the negative of the dealer delta change.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    gamma_component = sum(o.dealer_sign * o.confidence * o.gamma * o.open_interest * o.multiplier * price_change for o in options)
    vanna_component = sum(o.dealer_sign * o.confidence * o.vanna * o.open_interest * o.multiplier * iv_change for o in options)
    charm_component = sum(o.dealer_sign * o.confidence * o.charm * o.open_interest * o.multiplier * elapsed_years for o in options)
    delta_change = gamma_component + vanna_component + charm_component
    hedge = -delta_change
    if hedge > 0:
        direction = "buy_underlying"
    elif hedge < 0:
        direction = "sell_underlying"
    else:
        direction = "neutral"
    confidence = min(1.0, sum(abs(o.confidence) for o in options) / max(1, len(options)))
    return HedgePressure(
        spot=spot,
        gamma_component=gamma_component,
        vanna_component=vanna_component,
        charm_component=charm_component,
        total_delta_change=delta_change,
        estimated_hedge_demand=hedge,
        direction=direction,
        confidence=confidence,
    )
