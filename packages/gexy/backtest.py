from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, TypeVar

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
