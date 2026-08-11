from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .baselines import BaselineForecast
from .calibration import CalibrationMetrics, score_forecasts
from .dataset import ResearchRow


@dataclass(frozen=True)
class ExperimentResult:
    name: str
    metrics: CalibrationMetrics


def run_experiment(
    name: str,
    rows: Sequence[ResearchRow],
    forecaster: Callable[[Sequence[ResearchRow]], list[BaselineForecast]],
) -> ExperimentResult:
    forecasts = forecaster(rows)
    metrics = score_forecasts(
        [item.up_probability for item in forecasts],
        [item.move_points for item in forecasts],
        [row.label for row in rows],
    )
    return ExperimentResult(name=name, metrics=metrics)
