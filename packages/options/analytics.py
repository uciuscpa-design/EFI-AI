from dataclasses import dataclass
from enum import StrEnum

from packages.options.greeks import black_scholes_gamma, implied_volatility
from packages.options.models import OptionContract, OptionSnapshot


class GammaSource(StrEnum):
    FEED_GAMMA = "feed_gamma"
    FEED_IV = "feed_iv"
    SOLVED_IV = "solved_iv"


@dataclass(frozen=True)
class DerivedOptionAnalytics:
    symbol: str
    mark: float
    implied_volatility: float | None
    gamma: float
    gamma_source: GammaSource


def derive_option_analytics(
    *,
    contract: OptionContract,
    snapshot: OptionSnapshot,
    spot: float,
    years_to_expiry: float,
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> DerivedOptionAnalytics:
    """Return a usable IV/gamma pair without hiding market-data assumptions.

    Priority:
    1. Use feed gamma when present; preserve feed IV when present.
    2. If only feed IV is present, calculate gamma from that IV.
    3. If neither is present, solve IV from the option mark and calculate gamma.

    The caller must supply spot and years_to_expiry explicitly. This module does
    not guess SPX from SPY and does not assume an option settlement timestamp.
    """
    if snapshot.symbol != contract.symbol:
        raise ValueError("contract and snapshot symbols must match")
    if spot <= 0:
        raise ValueError("spot must be positive")
    if years_to_expiry <= 0:
        raise ValueError("years_to_expiry must be positive")

    mark = snapshot.mark
    if mark is None or mark <= 0:
        raise ValueError("snapshot requires a positive option mark")

    feed_iv = snapshot.implied_volatility
    feed_gamma = snapshot.greeks.gamma if snapshot.greeks is not None else None

    if feed_gamma is not None:
        if feed_gamma < 0:
            raise ValueError("feed gamma cannot be negative")
        return DerivedOptionAnalytics(
            symbol=contract.symbol,
            mark=mark,
            implied_volatility=feed_iv if feed_iv is not None and feed_iv > 0 else None,
            gamma=feed_gamma,
            gamma_source=GammaSource.FEED_GAMMA,
        )

    if feed_iv is not None and feed_iv > 0:
        gamma = black_scholes_gamma(
            spot=spot,
            strike=contract.strike_price,
            years_to_expiry=years_to_expiry,
            volatility=feed_iv,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )
        return DerivedOptionAnalytics(
            symbol=contract.symbol,
            mark=mark,
            implied_volatility=feed_iv,
            gamma=gamma,
            gamma_source=GammaSource.FEED_IV,
        )

    solved_iv = implied_volatility(
        market_price=mark,
        spot=spot,
        strike=contract.strike_price,
        years_to_expiry=years_to_expiry,
        option_type=contract.option_type,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )
    gamma = black_scholes_gamma(
        spot=spot,
        strike=contract.strike_price,
        years_to_expiry=years_to_expiry,
        volatility=solved_iv,
        risk_free_rate=risk_free_rate,
        dividend_yield=dividend_yield,
    )
    return DerivedOptionAnalytics(
        symbol=contract.symbol,
        mark=mark,
        implied_volatility=solved_iv,
        gamma=gamma,
        gamma_source=GammaSource.SOLVED_IV,
    )
