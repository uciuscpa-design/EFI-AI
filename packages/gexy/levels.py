from __future__ import annotations

from dataclasses import dataclass

from .gex import calculate_gex_by_strike
from .models import OptionContract


@dataclass(frozen=True)
class GammaLevels:
    gamma_flip: float | None
    call_wall: float | None
    put_wall: float | None
    gex_by_strike: dict[float, float]


def detect_levels(contracts: list[OptionContract], spot: float) -> GammaLevels:
    snapshot = calculate_gex_by_strike(contracts, spot=spot)
    ordered = sorted(snapshot.by_strike.items())
    if not ordered:
        return GammaLevels(None, None, None, {})

    flip = None
    previous = ordered[0]
    for current in ordered[1:]:
        if previous[1] == 0 or current[1] == 0 or (previous[1] < 0 < current[1]) or (previous[1] > 0 > current[1]):
            flip = min(previous[0], current[0], key=lambda x: abs(x - spot))
            break
        previous = current

    calls = [(strike, value) for strike, value in ordered if next((c.option_type for c in contracts if c.strike == strike), None) == "call"]
    puts = [(strike, value) for strike, value in ordered if next((c.option_type for c in contracts if c.strike == strike), None) == "put"]
    call_wall = max(calls, key=lambda item: abs(item[1]))[0] if calls else None
    put_wall = max(puts, key=lambda item: abs(item[1]))[0] if puts else None
    return GammaLevels(flip, call_wall, put_wall, snapshot.by_strike)
