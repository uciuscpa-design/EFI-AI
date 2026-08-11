from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .calibration import CalibrationMetrics, score_forecasts
from .dataset import ResearchRow
from .model import fit_ridge, predict


@dataclass(frozen=True)
class SplitResult:
    name: str
    samples: int
    metrics: CalibrationMetrics


@dataclass(frozen=True)
class ChronologicalReport:
    train: SplitResult
    validation: SplitResult
    test: SplitResult


def _evaluate(rows: Sequence[ResearchRow], model) -> SplitResult:
    if not rows:
        return SplitResult("empty", 0, score_forecasts([], [], []))
    predictions = [predict(model, row) for row in rows]
    return SplitResult(
        "evaluation",
        len(rows),
        score_forecasts(
            [p.up_probability for p in predictions],
            [p.move_points for p in predictions],
            [r.label for r in rows],
        ),
    )


def run_chronological(
    train: Sequence[ResearchRow],
    validation: Sequence[ResearchRow],
    test: Sequence[ResearchRow],
    *,
    alpha: float = 1.0,
) -> ChronologicalReport:
    """Fit only on train, evaluate validation/test without refitting.

    Hyperparameter selection should happen outside the locked test period. This
    function intentionally has no test-set tuning path.
    """
    if not train:
        raise ValueError("training set cannot be empty")
    model = fit_ridge(train, alpha=alpha)
    train_result = _evaluate(train, model)
    validation_result = _evaluate(validation, model)
    test_result = _evaluate(test, model)
    return ChronologicalReport(
        SplitResult("train", train_result.samples, train_result.metrics),
        SplitResult("validation", validation_result.samples, validation_result.metrics),
        SplitResult("test", test_result.samples, test_result.metrics),
    )
