from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class Side(StrEnum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: float
    ask: float
    timestamp: datetime

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: Side
    quantity: float
    reference_price: float
    created_at: datetime

    @classmethod
    def now(cls, symbol: str, side: Side, quantity: float, reference_price: float) -> "OrderIntent":
        return cls(symbol, side, quantity, reference_price, datetime.now(timezone.utc))
