from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from .dataset import ResearchRow


@dataclass(frozen=True)
class BaselineForecast:
    up_probability: float
    move_points: float


def zero_move(rows: Sequence[ResearchRow]) -> list[BaselineForecast]:
    return [BaselineForecast(0.5, 0.0) for _ in rows]


def recent_move(rows: Sequence[ResearchRow]) -> list[BaselineForecast]:
    result: list[BaselineForecast] = []
    for row in rows:
        move = row.spot_change
        result.append(BaselineForecast(0.5 + 0.25 * (1 if move > 0 else -1 if move < 0 else 0), move))
    return result


def hedge_pressure(rows: Sequence[ResearchRow], scale: float = 1.0) -> list[BaselineForecast]:
    if scale <= 0:
        raise ValueError("scale must be positive")
    result: list[BaselineForecast] = []
    for row in rows:
        normalized = row.estimated_hedge_demand / scale
        probability = 1.0 / (1.0 + pow(2.718281828459045, -normalized))
        result.append(BaselineForecast(probability, normalized * sqrt(max(row.label.horizon_minutes, 1))))
    return result
