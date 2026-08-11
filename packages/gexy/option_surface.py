from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .market_adapter import OptionSnapshot


@dataclass(frozen=True)
class StrikeExposure:
    strike: float
    gex: float
    vanna: float
    charm: float
    open_interest: float


@dataclass(frozen=True)
class PositioningSurface:
    strikes: tuple[StrikeExposure, ...]
    total_gex: float
    total_vanna: float
    total_charm: float
    call_wall: float | None
    put_wall: float | None


def aggregate_surface(options: Sequence[OptionSnapshot]) -> PositioningSurface:
    """Aggregate supplied option Greeks/OI without assuming a vendor's sign convention.

    The adapter is expected to normalize each option's signed Greek contribution.
    This function therefore sums the supplied call/put contributions rather than
    applying a hidden multiplier or dealer-position assumption.
    """
    by_strike: dict[float, list[float]] = {}
    for option in options:
        gex = option.call_gamma + option.put_gamma
        vanna = option.call_vanna + option.put_vanna
        charm = option.call_charm + option.put_charm
        oi = option.call_open_interest + option.put_open_interest
        values = by_strike.setdefault(option.strike, [0.0, 0.0, 0.0, 0.0])
        values[0] += gex
        values[1] += vanna
        values[2] += charm
        values[3] += oi
    strikes = tuple(
        StrikeExposure(k, *values) for k, values in sorted(by_strike.items())
    )
    call_wall = max(strikes, key=lambda x: x.open_interest).strike if strikes else None
    put_wall = min(strikes, key=lambda x: x.open_interest).strike if strikes else None
    return PositioningSurface(
        strikes,
        sum(x.gex for x in strikes),
        sum(x.vanna for x in strikes),
        sum(x.charm for x in strikes),
        call_wall,
        put_wall,
    )
