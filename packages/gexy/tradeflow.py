from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class AggressorSide(str, Enum):
    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AggressorClassification:
    side: AggressorSide
    signed_side: int
    reason: str
    bid: float
    ask: float
    midpoint: float | None
    spread: float | None


def classify_trade_against_nbbo(
    trade_price: float,
    bid_price: float,
    ask_price: float,
    *,
    tolerance: float = 1e-9,
) -> AggressorClassification:
    """Classify a trade using only the pre-trade NBBO.

    This rule is intentionally frozen before inspecting GEXY TCBBO samples.
    OPRA does not disseminate aggressor side, so the classifier does not use a
    vendor-side label as ground truth.

    Rules:
    - invalid, crossed, or locked NBBO -> unknown
    - trade at/above ask -> buy
    - trade at/below bid -> sell
    - inside spread above midpoint -> buy
    - inside spread below midpoint -> sell
    - at midpoint -> unknown

    The tolerance only protects floating-point comparisons; it is not a tuned
    market parameter.
    """
    trade = float(trade_price)
    bid = float(bid_price)
    ask = float(ask_price)
    tol = float(tolerance)

    if tol < 0:
        raise ValueError("tolerance must be nonnegative")

    if not (isfinite(trade) and isfinite(bid) and isfinite(ask)):
        return AggressorClassification(
            side=AggressorSide.UNKNOWN,
            signed_side=0,
            reason="nonfinite",
            bid=bid,
            ask=ask,
            midpoint=None,
            spread=None,
        )

    spread = ask - bid
    midpoint = (ask + bid) / 2.0

    if spread < -tol:
        return AggressorClassification(
            side=AggressorSide.UNKNOWN,
            signed_side=0,
            reason="crossed_nbbo",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    if spread <= tol:
        return AggressorClassification(
            side=AggressorSide.UNKNOWN,
            signed_side=0,
            reason="locked_nbbo",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    if trade >= ask - tol:
        return AggressorClassification(
            side=AggressorSide.BUY,
            signed_side=1,
            reason="at_or_above_ask",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    if trade <= bid + tol:
        return AggressorClassification(
            side=AggressorSide.SELL,
            signed_side=-1,
            reason="at_or_below_bid",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    if trade > midpoint + tol:
        return AggressorClassification(
            side=AggressorSide.BUY,
            signed_side=1,
            reason="inside_spread_above_mid",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    if trade < midpoint - tol:
        return AggressorClassification(
            side=AggressorSide.SELL,
            signed_side=-1,
            reason="inside_spread_below_mid",
            bid=bid,
            ask=ask,
            midpoint=midpoint,
            spread=spread,
        )

    return AggressorClassification(
        side=AggressorSide.UNKNOWN,
        signed_side=0,
        reason="midpoint",
        bid=bid,
        ask=ask,
        midpoint=midpoint,
        spread=spread,
    )
