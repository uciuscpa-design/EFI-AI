from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PricePoint:
    timestamp: datetime
    price: float


@dataclass(frozen=True)
class ForwardLabel:
    origin: datetime
    horizon_minutes: int
    origin_price: float
    future_timestamp: datetime | None
    future_price: float | None
    return_pct: float | None


def build_forward_labels(
    origins: Iterable[PricePoint],
    prices: Sequence[PricePoint],
    horizons_minutes: Sequence[int] = (1, 5, 15, 30, 60),
) -> list[ForwardLabel]:
    """Build point-in-time forward returns without using prices before origin.

    For each origin and horizon, the first price at or after origin+horizon is
    selected. If the replay data does not reach the requested horizon, the
    future fields remain null instead of shortening the horizon silently.
    """
    ordered = sorted(prices, key=lambda p: p.timestamp)
    if any(p.price <= 0 for p in ordered):
        raise ValueError("prices must be positive")
    if any(h <= 0 for h in horizons_minutes):
        raise ValueError("horizons must be positive")

    result: list[ForwardLabel] = []
    for origin in origins:
        if origin.price <= 0:
            raise ValueError("origin price must be positive")
        for horizon in horizons_minutes:
            target = origin.timestamp + timedelta(minutes=horizon)
            future = next((p for p in ordered if p.timestamp >= target), None)
            result.append(
                ForwardLabel(
                    origin=origin.timestamp,
                    horizon_minutes=horizon,
                    origin_price=origin.price,
                    future_timestamp=future.timestamp if future else None,
                    future_price=future.price if future else None,
                    return_pct=(100.0 * (future.price / origin.price - 1.0)) if future else None,
                )
            )
    return result
