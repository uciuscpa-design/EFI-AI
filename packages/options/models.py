from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


class OptionStyle(StrEnum):
    AMERICAN = "american"
    EUROPEAN = "european"


@dataclass(frozen=True)
class OptionContract:
    symbol: str
    underlying_symbol: str
    root_symbol: str
    expiration_date: date
    strike_price: float
    option_type: OptionType
    style: OptionStyle
    multiplier: float
    open_interest: float | None = None
    open_interest_date: date | None = None


@dataclass(frozen=True)
class OptionGreeks:
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None


@dataclass(frozen=True)
class OptionSnapshot:
    symbol: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    quote_timestamp: datetime | None = None
    trade_timestamp: datetime | None = None
    implied_volatility: float | None = None
    greeks: OptionGreeks | None = None

    @property
    def mark(self) -> float | None:
        if self.bid is not None and self.ask is not None and self.bid >= 0 and self.ask >= self.bid:
            return (self.bid + self.ask) / 2
        return self.last
