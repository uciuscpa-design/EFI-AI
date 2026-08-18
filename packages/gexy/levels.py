from __future__ import annotations

from dataclasses import dataclass

from packages.gexy.models import GexStrikeLevel, GexSurface


@dataclass(frozen=True)
class GexWallSummary:
    """High-signal strike landmarks derived from one GEX surface."""

    strongest_unsigned: GexStrikeLevel | None
    strongest_positive_heuristic: GexStrikeLevel | None
    strongest_negative_heuristic: GexStrikeLevel | None
    nearest_above_spot: GexStrikeLevel | None
    nearest_below_spot: GexStrikeLevel | None


def summarize_gex_walls(surface: GexSurface) -> GexWallSummary:
    """Extract useful strike landmarks without pretending they predict direction.

    `strongest_unsigned` is the strike with the largest absolute gamma-exposure
    magnitude. Positive/negative fields use GEXY's explicitly heuristic signed
    convention. Nearest-above/below are proximity landmarks among computed levels.
    """
    levels = surface.levels
    strongest_unsigned = max(levels, key=lambda level: level.unsigned_gex_per_1pct, default=None)

    positive = [
        level for level in levels if level.heuristic_signed_gex_per_1pct > 0
    ]
    negative = [
        level for level in levels if level.heuristic_signed_gex_per_1pct < 0
    ]
    above = [level for level in levels if level.strike >= surface.spot]
    below = [level for level in levels if level.strike <= surface.spot]

    return GexWallSummary(
        strongest_unsigned=strongest_unsigned,
        strongest_positive_heuristic=max(
            positive,
            key=lambda level: level.heuristic_signed_gex_per_1pct,
            default=None,
        ),
        strongest_negative_heuristic=min(
            negative,
            key=lambda level: level.heuristic_signed_gex_per_1pct,
            default=None,
        ),
        nearest_above_spot=min(above, key=lambda level: level.strike, default=None),
        nearest_below_spot=max(below, key=lambda level: level.strike, default=None),
    )


def rank_levels_by_unsigned_gex(surface: GexSurface, limit: int = 10) -> tuple[GexStrikeLevel, ...]:
    """Return the largest gamma-exposure strikes, descending by magnitude."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    return tuple(
        sorted(
            surface.levels,
            key=lambda level: level.unsigned_gex_per_1pct,
            reverse=True,
        )[:limit]
    )
