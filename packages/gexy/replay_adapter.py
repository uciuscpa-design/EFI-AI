from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator

from .market_adapter import MarketSnapshot


class ReplayAdapter:
    """Replay normalized snapshots through the same interface as a live provider."""

    def __init__(self, snapshots: AsyncIterable[MarketSnapshot], *, interval_seconds: float = 0.0) -> None:
        if interval_seconds < 0:
            raise ValueError("interval_seconds must be non-negative")
        self._source = snapshots
        self._interval = interval_seconds

    async def snapshots(self) -> AsyncIterator[MarketSnapshot]:
        async for snapshot in self._source:
            yield snapshot
            if self._interval:
                await asyncio.sleep(self._interval)
