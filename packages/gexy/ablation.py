from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from .calibration import CalibrationMetrics
from .dataset import ResearchRow
from .evaluation import EvaluationResult, evaluate


@dataclass(frozen=True)
class MetricDelta:
    directional_accuracy: float
    mean_absolute_error: float
    mean_bias_absolute: float
    brier_score: float


@dataclass(frozen=True)
class RegimeAblationResult:
    with_regime: EvaluationResult
    without_regime: EvaluationResult
    improvement: MetricDelta


def _improvement(with_score: CalibrationMetrics, without_score: CalibrationMetrics) -> MetricDelta:
    """Return positive values when the regime feature improves a metric.

    Accuracy is higher-is-better. MAE, absolute bias and Brier score are
    lower-is-better, so their deltas are reversed. Absolute bias is compared
    because a bias closer to zero is preferable regardless of sign.
    """
    return MetricDelta(
        directional_accuracy=with_score.directional_accuracy - without_score.directional_accuracy,
        mean_absolute_error=without_score.mean_absolute_error - with_score.mean_absolute_error,
        mean_bias_absolute=abs(without_score.mean_bias) - abs(with_score.mean_bias),
        brier_score=without_score.brier_score - with_score.brier_score,
    )


def evaluate_regime_ablation(
    rows: Sequence[ResearchRow], *, alpha: float = 1.0
) -> RegimeAblationResult:
    """Compare identical chronological evaluations with and without regime_score.

    The control preserves every row, timestamp, label and non-regime feature and
    only forces regime_score to zero. Both arms therefore receive identical
    chronological train/validation/test boundaries.
    """
    with_regime = evaluate(rows, alpha=alpha)
    control_rows = [replace(row, regime_score=0.0) for row in rows]
    without_regime = evaluate(control_rows, alpha=alpha)
    return RegimeAblationResult(
        with_regime=with_regime,
        without_regime=without_regime,
        improvement=_improvement(with_regime.test_metrics, without_regime.test_metrics),
    )
