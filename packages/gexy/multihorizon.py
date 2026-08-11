from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .calibration import CalibrationMetrics
from .dataset import ResearchRow
from .model_compare import ComparisonResult, compare_models


@dataclass(frozen=True)
class HorizonResult:
    horizon_minutes: int
    results: tuple[ComparisonResult, ...]


def run_horizons(
    datasets: dict[int, Sequence[ResearchRow]],
    *,
    alpha: float = 1.0,
) -> list[HorizonResult]:
    """Run the same model comparison independently for each horizon dataset."""
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    output: list[HorizonResult] = []
    for horizon in sorted(datasets):
        rows = datasets[horizon]
        if not rows:
            continue
        output.append(HorizonResult(horizon, tuple(compare_models(rows, alpha=alpha))))
    return output
