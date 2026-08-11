from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .backtest import chronological_split
from .calibration import CalibrationMetrics, score_forecasts
from .dataset import ResearchRow
from .model import LinearModel, fit_ridge, predict


@dataclass(frozen=True)
class ComparisonResult:
    name: str
    test_metrics: CalibrationMetrics


def _project(row: ResearchRow, name: str) -> ResearchRow:
    if name == "gex":
        return ResearchRow(**{**row.__dict__, "gamma_change": 0, "vanna_component": 0, "charm_component": 0, "estimated_hedge_demand": 0, "iv_change": 0, "spot_change": 0})
    if name == "gex_vanna":
        return ResearchRow(**{**row.__dict__, "charm_component": 0, "estimated_hedge_demand": 0})
    if name == "gex_vanna_charm":
        return ResearchRow(**{**row.__dict__, "estimated_hedge_demand": 0})
    if name == "full":
        return row
    raise ValueError(f"unknown model: {name}")


def compare_models(rows: Sequence[ResearchRow], *, alpha: float = 1.0) -> list[ComparisonResult]:
    split = chronological_split(rows)
    if not split.train or not split.validation or not split.test:
        raise ValueError("train, validation and test sets must all contain samples")
    results: list[ComparisonResult] = []
    for name in ("gex", "gex_vanna", "gex_vanna_charm", "full"):
        train = [_project(row, name) for row in split.train]
        test = [_project(row, name) for row in split.test]
        model: LinearModel = fit_ridge(train, alpha=alpha)
        predictions = [predict(model, row) for row in test]
        metrics = score_forecasts(
            [prediction.up_probability for prediction in predictions],
            [prediction.move_points for prediction in predictions],
            [row.label for row in test],
        )
        results.append(ComparisonResult(name, metrics))
    return results
