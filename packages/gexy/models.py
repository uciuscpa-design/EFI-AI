from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class OptionContract:
    """Normalized option snapshot used by GEXY calculations."""

    symbol: str
    underlying: str
    strike: float
    expiration: datetime
    option_type: str  # call | put
    open_interest: float
    gamma: float
    delta: float = 0.0
    vanna: float = 0.0
    charm: float = 0.0
    implied_volatility: float = 0.0
    multiplier: float = 100.0
    dealer_sign: float = -1.0
    confidence: float = 0.5

    def __post_init__(self) -> None:
        if self.option_type not in {"call", "put"}:
            raise ValueError("option_type must be 'call' or 'put'")
        if self.strike <= 0:
            raise ValueError("strike must be positive")
        if self.open_interest < 0:
            raise ValueError("open_interest cannot be negative")
        if self.multiplier <= 0:
            raise ValueError("multiplier must be positive")
        if not -1.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between -1 and 1")


@dataclass(frozen=True)
class GEXSnapshot:
    spot: float
    by_strike: dict[float, float]
    total: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class HedgePressure:
    spot: float
    gamma_component: float
    vanna_component: float
    charm_component: float
    total_delta_change: float
    estimated_hedge_demand: float
    direction: str
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
