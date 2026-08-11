from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar

from .market_adapter import MarketSnapshot

T = TypeVar("T")


@dataclass(frozen=True)
class TimeSplit:
    train: list[T]
    validation: list[T]
    test: list[T]


def chronological_split(
    samples: Sequence[T],
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
) -> TimeSplit[T]:
    """Split ordered samples without shuffling or temporal leakage."""
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("fractions must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train + validation fractions must be < 1")
    n = len(samples)
    train_end = int(n * train_fraction)
    validation_end = train_end + int(n * validation_fraction)
    return TimeSplit(
        train=list(samples[:train_end]),
        validation=list(samples[train_end:validation_end]),
        test=list(samples[validation_end:]),
    )


@dataclass(frozen=True)
class BacktestPoint:
    timestamp: object
    spot: float
    horizon_minutes: int
    predicted_move: float
    actual_move: float


def forward_move(spots: Sequence[float], index: int, steps: int) -> float | None:
    target = index + steps
    if index < 0 or target >= len(spots):
        return None
    return spots[target] - spots[index]


def chronological_points(
    snapshots: Sequence[MarketSnapshot],
    predictions: Sequence[float],
    *,
    horizon_steps: int,
    horizon_minutes: int,
) -> list[BacktestPoint]:
    """Pair predictions with strictly later observations; no look-ahead labels."""
    if len(snapshots) != len(predictions):
        raise ValueError("snapshots and predictions must have equal length")
    if horizon_steps <= 0:
        raise ValueError("horizon_steps must be positive")
    spots = [s.spot for s in snapshots]
    result: list[BacktestPoint] = []
    for i, (snapshot, prediction) in enumerate(zip(snapshots, predictions)):
        actual = forward_move(spots, i, horizon_steps)
        if actual is None:
            continue
        result.append(BacktestPoint(snapshot.timestamp, snapshot.spot, horizon_minutes, prediction, actual))
    return result
