from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class PriceSnapshot:
    timestamp: datetime
    symbol: str
    price: float
    volume: float | None = None


@dataclass(frozen=True)
class OptionSnapshot:
    timestamp: datetime
    contract_id: str
    underlying: str
    strike: float
    expiration: datetime
    option_type: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    iv: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    open_interest: float | None = None
    volume: float | None = None
    trade_direction: str | None = None


@dataclass(frozen=True)
class FeatureSnapshot:
    timestamp: datetime
    spx: PriceSnapshot
    es: PriceSnapshot | None
    options: tuple[OptionSnapshot, ...]


def synchronize(
    spx: Iterable[PriceSnapshot],
    *,
    es: Iterable[PriceSnapshot] = (),
    options: Iterable[OptionSnapshot] = (),
) -> list[FeatureSnapshot]:
    """Group already-normalized records by exact timestamp.

    Provider-specific timestamp alignment/interpolation belongs in adapters. This
    core function deliberately refuses to invent prices between observations.
    """
    spx_by_time = {row.timestamp: row for row in spx}
    es_by_time = {row.timestamp: row for row in es}
    options_by_time: dict[datetime, list[OptionSnapshot]] = {}
    for row in options:
        options_by_time.setdefault(row.timestamp, []).append(row)

    result: list[FeatureSnapshot] = []
    for timestamp in sorted(spx_by_time):
        result.append(
            FeatureSnapshot(
                timestamp=timestamp,
                spx=spx_by_time[timestamp],
                es=es_by_time.get(timestamp),
                options=tuple(options_by_time.get(timestamp, [])),
            )
        )
    return result
