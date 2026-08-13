from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .dataset import ResearchRow
from .evaluation import EvaluationResult, evaluate
from .recording import RecordedSnapshot
from .session_dataset import build_session_rows


@dataclass(frozen=True)
class HorizonScorecard:
    horizon_minutes: int
    samples: int
    train_samples: int
    validation_samples: int
    test_samples: int
    directional_accuracy: float | None
    mean_absolute_error: float | None
    mean_bias: float | None
    brier_score: float | None
    status: str


def _as_research_row(row) -> ResearchRow:
    return ResearchRow(
        timestamp=row.timestamp,
        spot=row.spot,
        spot_change=row.spot_change,
        iv_change=row.iv_change,
        total_gex=row.total_gex,
        gamma_change=row.gamma_change,
        vanna_component=row.total_vanna,
        charm_component=row.total_charm,
        estimated_hedge_demand=row.estimated_hedge_demand,
        positioning_confidence=row.positioning_confidence,
        label=row.label,
    )


def build_scorecard(
    snapshots: Iterable[RecordedSnapshot],
    *,
    horizons_minutes: tuple[int, ...] = (1, 5, 15, 30, 60),
    alpha: float = 1.0,
    min_samples: int = 15,
) -> tuple[HorizonScorecard, ...]:
    """Evaluate each horizon independently with chronological train/validation/test splits.

    A horizon with too few rows is reported as insufficient instead of fitting an
    unstable model. No shuffling is performed and labels are created strictly from
    later observations by ``build_session_rows``.
    """
    if min_samples < 5:
        raise ValueError("min_samples must be at least 5")
    rows = build_session_rows(snapshots, horizons_minutes=horizons_minutes)
    result: list[HorizonScorecard] = []
    for horizon in horizons_minutes:
        horizon_rows = [_as_research_row(row) for row in rows if row.horizon_minutes == horizon]
        if len(horizon_rows) < min_samples:
            result.append(HorizonScorecard(horizon, len(horizon_rows), 0, 0, 0, None, None, None, None, "insufficient_data"))
            continue
        try:
            evaluation: EvaluationResult = evaluate(horizon_rows, alpha=alpha)
        except ValueError:
            result.append(HorizonScorecard(horizon, len(horizon_rows), 0, 0, 0, None, None, None, None, "insufficient_split"))
            continue
        metrics = evaluation.test_metrics
        result.append(
            HorizonScorecard(
                horizon_minutes=horizon,
                samples=len(horizon_rows),
                train_samples=evaluation.train_samples,
                validation_samples=evaluation.validation_samples,
                test_samples=evaluation.test_samples,
                directional_accuracy=metrics.directional_accuracy,
                mean_absolute_error=metrics.mean_absolute_error,
                mean_bias=metrics.mean_bias,
                brier_score=metrics.brier_score,
                status="ok",
            )
        )
    return tuple(result)
