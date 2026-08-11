from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .backtest import chronological_split
from .calibration import CalibrationMetrics, score_forecasts
from .dataset import ResearchRow
from .model import fit_ridge, predict


@dataclass(frozen=True)
class EvaluationResult:
    train_samples: int
    validation_samples: int
    test_samples: int
    test_metrics: CalibrationMetrics


def evaluate(rows: Sequence[ResearchRow], *, alpha: float = 1.0) -> EvaluationResult:
    split = chronological_split(rows)
    if not split.train or not split.validation or not split.test:
        raise ValueError("train, validation and test sets must all contain samples")

    # Fit only on the training period. Validation is reserved for future hyper-
    # parameter selection; the current baseline uses the supplied alpha directly.
    model = fit_ridge(split.train, alpha=alpha)
    probabilities = [predict(model, row).up_probability for row in split.test]
    moves = [predict(model, row).move_points for row in split.test]
    metrics = score_forecasts(probabilities, moves, [row.label for row in split.test])
    return EvaluationResult(
        train_samples=len(split.train),
        validation_samples=len(split.validation),
        test_samples=len(split.test),
        test_metrics=metrics,
    )
