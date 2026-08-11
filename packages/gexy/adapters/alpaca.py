from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class AlpacaOptionsQuery:
    """Provider-neutral query description for the Alpaca adapter.

    The runtime adapter is intentionally isolated from the mathematical engine so
    provider payloads can be normalized without coupling GEXY to one vendor.
    """

    underlying: str
    expiration_gte: date | None = None
    expiration_lte: date | None = None
    strike_gte: float | None = None
    strike_lte: float | None = None
    feed: str = "indicative"


@dataclass(frozen=True)
class ProviderCapabilities:
    options_chain: bool
    greeks: bool
    open_interest: bool
    trade_direction: bool
    historical_options: bool


def capabilities() -> ProviderCapabilities:
    # Alpaca's chain endpoint exposes quotes/trades/IV/Greeks. OI and historical
    # options depth require separate provider handling and are not assumed here.
    return ProviderCapabilities(
        options_chain=True,
        greeks=True,
        open_interest=False,
        trade_direction=False,
        historical_options=False,
    )
