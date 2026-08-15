from __future__ import annotations

import math

import pytest

from packages.gexy.tradeflow import AggressorSide, classify_trade_against_nbbo


@pytest.mark.parametrize(
    ("trade", "bid", "ask", "expected_side", "expected_reason"),
    [
        (2.10, 2.00, 2.10, AggressorSide.BUY, "at_or_above_ask"),
        (2.12, 2.00, 2.10, AggressorSide.BUY, "at_or_above_ask"),
        (2.00, 2.00, 2.10, AggressorSide.SELL, "at_or_below_bid"),
        (1.98, 2.00, 2.10, AggressorSide.SELL, "at_or_below_bid"),
        (2.08, 2.00, 2.10, AggressorSide.BUY, "inside_spread_above_mid"),
        (2.02, 2.00, 2.10, AggressorSide.SELL, "inside_spread_below_mid"),
        (2.05, 2.00, 2.10, AggressorSide.UNKNOWN, "midpoint"),
        (2.05, 2.05, 2.05, AggressorSide.UNKNOWN, "locked_nbbo"),
        (2.05, 2.10, 2.00, AggressorSide.UNKNOWN, "crossed_nbbo"),
    ],
)
def test_classify_trade_against_nbbo_frozen_rules(
    trade: float,
    bid: float,
    ask: float,
    expected_side: AggressorSide,
    expected_reason: str,
) -> None:
    result = classify_trade_against_nbbo(trade, bid, ask)

    assert result.side is expected_side
    assert result.reason == expected_reason
    assert result.signed_side == {
        AggressorSide.BUY: 1,
        AggressorSide.SELL: -1,
        AggressorSide.UNKNOWN: 0,
    }[expected_side]


def test_nonfinite_quote_is_unknown() -> None:
    result = classify_trade_against_nbbo(2.05, math.nan, 2.10)

    assert result.side is AggressorSide.UNKNOWN
    assert result.signed_side == 0
    assert result.reason == "nonfinite"


def test_negative_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="tolerance"):
        classify_trade_against_nbbo(2.05, 2.00, 2.10, tolerance=-1e-6)
