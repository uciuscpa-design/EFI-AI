from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol


@dataclass(frozen=True)
class OptionSnapshot:
    symbol: str
    strike: float
    expiry: datetime
    call_open_interest: float = 0.0
    put_open_interest: float = 0.0
    call_gamma: float = 0.0
    put_gamma: float = 0.0
    call_vanna: float = 0.0
    put_vanna: float = 0.0
    call_charm: float = 0.0
    put_charm: float = 0.0
    implied_volatility: float | None = None


@dataclass(frozen=True)
class MarketSnapshot:
    timestamp: datetime
    spot: float
    iv: float | None
    options: tuple[OptionSnapshot, ...]


class MarketDataAdapter(Protocol):
    async def snapshots(self) -> AsyncIterator[MarketSnapshot]:
        """Yield normalized point-in-time market snapshots."""
        ...
