from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class OptionSurfacePoint:
    symbol: str
    underlying_symbol: str
    expiration_date: date
    option_type: OptionType
    strike: float
    multiplier: float
    open_interest: float
    open_interest_date: date | None = None
    bid: float | None = None
    ask: float | None = None
    bid_size: float | None = None
    ask_size: float | None = None
    quote_timestamp: datetime | None = None
    trade_price: float | None = None
    trade_size: float | None = None
    trade_timestamp: datetime | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None
    rho: float | None = None

    @property
    def mid(self) -> float | None:
        if self.bid is None or self.ask is None or self.bid < 0 or self.ask < self.bid:
            return None
        return (self.bid + self.ask) / 2

    @property
    def has_gamma(self) -> bool:
        return self.gamma is not None and self.gamma >= 0


@dataclass(frozen=True)
class NormalizedOptionSurface:
    points: tuple[OptionSurfacePoint, ...]
    contracts_seen: int
    invalid_contracts: int
    missing_snapshots: int


@dataclass(frozen=True)
class GexContribution:
    symbol: str
    strike: float
    option_type: OptionType
    open_interest: float
    gamma: float
    gamma_shares_per_point: float
    gax_notional_per_point: float
    unsigned_gex_per_1pct: float
    heuristic_signed_gax_per_point: float
    heuristic_signed_gex_per_1pct: float
    delta_notional: float | None


@dataclass(frozen=True)
class GexStrikeLevel:
    strike: float
    contracts: int
    gamma_shares_per_point: float
    gax_notional_per_point: float
    unsigned_gex_per_1pct: float
    heuristic_signed_gax_per_point: float
    heuristic_signed_gex_per_1pct: float
    delta_notional: float


@dataclass(frozen=True)
class GexSurface:
    spot: float
    levels: tuple[GexStrikeLevel, ...]
    contracts_seen: int
    contracts_used: int
    contracts_missing_gamma: int
    total_gax_notional_per_point: float
    total_unsigned_gex_per_1pct: float
    total_heuristic_signed_gax_per_point: float
    total_heuristic_signed_gex_per_1pct: float
    total_delta_notional: float
