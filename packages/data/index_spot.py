from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class IndexLevel:
    symbol: str
    value: float
    timestamp: datetime
    source: str

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("index value must be positive")
        if not self.source:
            raise ValueError("index source is required")


class IndexSpotProvider(Protocol):
    """Boundary for a validated machine-readable index-level source."""

    def level(self, symbol: str) -> IndexLevel:
        ...
