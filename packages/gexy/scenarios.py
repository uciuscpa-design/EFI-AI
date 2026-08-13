from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Sequence

from .gex import calculate_gex_by_strike
from .models import OptionContract


@dataclass(frozen=True)
class ScenarioPoint:
    scenario: str
    spot: float
    spot_change: float
    signed_gex: float
    estimated_hedge_demand: float
    hedge_direction: str


def _scenario_sign(option: OptionContract, scenario: str) -> float:
    if scenario == "long_gamma":
        return 1.0
    if scenario == "short_gamma":
        return -1.0
    if scenario == "mixed":
        # Transparent, deliberately simple mixed hypothesis: calls long gamma,
        # puts short gamma. This is not asserted dealer truth; it is a stress case.
        return 1.0 if option.option_type == "call" else -1.0
    raise ValueError(f"unknown scenario: {scenario}")


def apply_scenario(options: Iterable[OptionContract], scenario: str) -> list[OptionContract]:
    return [replace(option, dealer_sign=_scenario_sign(option, scenario)) for option in options]


def scenario_sensitivity(
    options: Sequence[OptionContract],
    *,
    reference_spot: float,
    moves: Sequence[float] = (-50.0, -25.0, -10.0, 10.0, 25.0, 50.0),
    scenarios: Sequence[str] = ("long_gamma", "short_gamma", "mixed"),
) -> list[ScenarioPoint]:
    """Stress signed gamma and hedge demand across hypothetical SPX moves.

    ``estimated_hedge_demand`` uses the first-order gamma relation
    ``-GEX * dS / (spot * 0.01)`` to express the hedge response in dollar-delta
    units implied by the project's GEX scaling. Positive values mean estimated
    dealer buying; negative values mean estimated dealer selling.
    """
    if reference_spot <= 0:
        raise ValueError("reference_spot must be positive")
    if not options:
        return []

    result: list[ScenarioPoint] = []
    for scenario in scenarios:
        scenario_options = apply_scenario(options, scenario)
        for move in moves:
            spot = reference_spot + float(move)
            if spot <= 0:
                raise ValueError("scenario spot must be positive")
            signed_gex = calculate_gex_by_strike(scenario_options, spot).total
            hedge = -signed_gex * float(move) / (spot * 0.01)
            if hedge > 0:
                direction = "buy"
            elif hedge < 0:
                direction = "sell"
            else:
                direction = "flat"
            result.append(
                ScenarioPoint(
                    scenario=scenario,
                    spot=spot,
                    spot_change=float(move),
                    signed_gex=signed_gex,
                    estimated_hedge_demand=hedge,
                    hedge_direction=direction,
                )
            )
    return result
