from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from packages.gexy.exposure import build_gex_surface
from packages.gexy.greeks import enrich_missing_greeks
from packages.gexy.levels import GexWallSummary, summarize_gex_walls
from packages.gexy.models import GexSurface, NormalizedOptionSurface, OptionSurfacePoint


@dataclass(frozen=True)
class GreekSourceCounts:
    alpaca: int = 0
    alpaca_iv: int = 0
    quote_implied_iv: int = 0
    unavailable: int = 0


@dataclass(frozen=True)
class GexySurfaceResult:
    spot: float
    points: tuple[OptionSurfacePoint, ...]
    surface: GexSurface
    walls: GexWallSummary
    greek_sources: GreekSourceCounts


def build_enriched_gexy_surface(
    normalized: NormalizedOptionSurface,
    *,
    spot: float,
    time_to_expiry_years: Mapping[date, float],
    risk_free_rate: float = 0.0,
    dividend_yield: float = 0.0,
) -> GexySurfaceResult:
    """Enrich nullable Greeks, aggregate GEX/GAX, and extract strike landmarks.

    Expiry timing is intentionally supplied by the caller. GEXY does not assume a
    universal SPX settlement time because SPX/SPXW series can have different
    settlement conventions.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")

    enriched_points: list[OptionSurfacePoint] = []
    source_counts = {
        "alpaca": 0,
        "alpaca_iv": 0,
        "quote_implied_iv": 0,
        "unavailable": 0,
    }

    for point in normalized.points:
        tte = time_to_expiry_years.get(point.expiration_date)
        if tte is None or tte <= 0:
            enriched_points.append(point)
            source_counts["unavailable"] += 1
            continue

        enrichment = enrich_missing_greeks(
            point,
            spot=spot,
            time_to_expiry_years=tte,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield,
        )
        enriched_points.append(enrichment.point)
        source_counts[enrichment.source] += 1

    surface = build_gex_surface(enriched_points, spot)
    return GexySurfaceResult(
        spot=spot,
        points=tuple(enriched_points),
        surface=surface,
        walls=summarize_gex_walls(surface),
        greek_sources=GreekSourceCounts(**source_counts),
    )
