from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from packages.gexy.models import (
    GexContribution,
    GexStrikeLevel,
    GexSurface,
    OptionSurfacePoint,
    OptionType,
)


def _heuristic_sign(option_type: OptionType) -> float:
    """Legacy call-positive / put-negative sign convention.

    This is a transparent heuristic for structural comparison. It is not a claim
    about observed dealer inventory or trade direction.
    """
    return 1.0 if option_type is OptionType.CALL else -1.0


def contract_exposure(point: OptionSurfacePoint, spot: float) -> GexContribution | None:
    """Calculate contract-level hedge acceleration and gamma exposure.

    GEXY project definitions:
      gamma_shares_per_point = gamma * open_interest * multiplier
      GAX notional / point   = gamma_shares_per_point * spot
      GEX notional / 1% move = GAX_notional_per_point * (spot * 0.01)

    GAX here is deliberately defined as hedge-notional acceleration per one
    underlying point. It is a project metric, not a claim about a standardized
    industry/vendor definition.
    """
    if spot <= 0:
        raise ValueError("spot must be positive")
    if point.gamma is None or point.gamma < 0:
        return None

    gamma_shares_per_point = point.gamma * point.open_interest * point.multiplier
    gax_notional_per_point = gamma_shares_per_point * spot
    unsigned_gex_per_1pct = gax_notional_per_point * spot * 0.01
    sign = _heuristic_sign(point.option_type)
    delta_notional = None
    if point.delta is not None:
        delta_notional = point.delta * point.open_interest * point.multiplier * spot

    return GexContribution(
        symbol=point.symbol,
        strike=point.strike,
        option_type=point.option_type,
        open_interest=point.open_interest,
        gamma=point.gamma,
        gamma_shares_per_point=gamma_shares_per_point,
        gax_notional_per_point=gax_notional_per_point,
        unsigned_gex_per_1pct=unsigned_gex_per_1pct,
        heuristic_signed_gax_per_point=gax_notional_per_point * sign,
        heuristic_signed_gex_per_1pct=unsigned_gex_per_1pct * sign,
        delta_notional=delta_notional,
    )


def build_gex_surface(points: Iterable[OptionSurfacePoint], spot: float) -> GexSurface:
    """Aggregate normalized option contracts into strike-level GEX/GAX metrics."""
    if spot <= 0:
        raise ValueError("spot must be positive")

    source_points = tuple(points)
    buckets: dict[float, list[GexContribution]] = defaultdict(list)
    missing_gamma = 0

    for point in source_points:
        contribution = contract_exposure(point, spot)
        if contribution is None:
            missing_gamma += 1
            continue
        buckets[point.strike].append(contribution)

    levels: list[GexStrikeLevel] = []
    for strike in sorted(buckets):
        contributions = buckets[strike]
        levels.append(
            GexStrikeLevel(
                strike=strike,
                contracts=len(contributions),
                gamma_shares_per_point=sum(item.gamma_shares_per_point for item in contributions),
                gax_notional_per_point=sum(item.gax_notional_per_point for item in contributions),
                unsigned_gex_per_1pct=sum(item.unsigned_gex_per_1pct for item in contributions),
                heuristic_signed_gax_per_point=sum(
                    item.heuristic_signed_gax_per_point for item in contributions
                ),
                heuristic_signed_gex_per_1pct=sum(
                    item.heuristic_signed_gex_per_1pct for item in contributions
                ),
                delta_notional=sum(item.delta_notional or 0.0 for item in contributions),
            )
        )

    return GexSurface(
        spot=spot,
        levels=tuple(levels),
        contracts_seen=len(source_points),
        contracts_used=sum(level.contracts for level in levels),
        contracts_missing_gamma=missing_gamma,
        total_gax_notional_per_point=sum(level.gax_notional_per_point for level in levels),
        total_unsigned_gex_per_1pct=sum(level.unsigned_gex_per_1pct for level in levels),
        total_heuristic_signed_gax_per_point=sum(
            level.heuristic_signed_gax_per_point for level in levels
        ),
        total_heuristic_signed_gex_per_1pct=sum(
            level.heuristic_signed_gex_per_1pct for level in levels
        ),
        total_delta_notional=sum(level.delta_notional for level in levels),
    )
