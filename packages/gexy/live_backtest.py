from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from statistics import mean
from typing import Sequence

from .live_pipeline import run_live_pipeline
from .market_adapter import MarketSnapshot


@dataclass(frozen=True)
class LiveBacktestPoint:
    timestamp: object
    spot: float
    future_spot: float
    horizon_minutes: int
    direction: str
    predicted_move: float
    actual_move: float
    confidence: float
    regime: str

    @property
    def direction_correct(self) -> bool:
        actual_direction = "up" if self.actual_move > 0 else "down" if self.actual_move < 0 else "flat"
        return self.direction == actual_direction


@dataclass(frozen=True)
class LiveBacktestSummary:
    samples: int
    directional_accuracy: float
    mean_absolute_error: float
    root_mean_squared_error: float
    mean_bias: float
    mean_confidence: float
    calibration_gap: float


def replay_live_pipeline(
    snapshots: Sequence[MarketSnapshot],
    *,
    horizon_steps: int,
    horizon_minutes: int,
) -> tuple[LiveBacktestPoint, ...]:
    """Replay the deterministic live predictor chronologically without look-ahead.

    Each prediction is produced only from snapshot[i]. The realized move is attached
    afterward from snapshot[i + horizon_steps].
    """
    if horizon_steps <= 0:
        raise ValueError("horizon_steps must be positive")
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")

    points: list[LiveBacktestPoint] = []
    for index, snapshot in enumerate(snapshots):
        future_index = index + horizon_steps
        if future_index >= len(snapshots):
            break
        result = run_live_pipeline(snapshot, horizon_minutes=horizon_minutes)
        future_spot = snapshots[future_index].spot
        actual_move = future_spot - snapshot.spot
        prediction = result.prediction
        points.append(
            LiveBacktestPoint(
                timestamp=snapshot.timestamp,
                spot=float(snapshot.spot),
                future_spot=float(future_spot),
                horizon_minutes=horizon_minutes,
                direction=prediction.direction,
                predicted_move=float(prediction.expected_move_points),
                actual_move=float(actual_move),
                confidence=float(prediction.confidence),
                regime=prediction.regime,
            )
        )
    return tuple(points)


def summarize_live_backtest(points: Sequence[LiveBacktestPoint]) -> LiveBacktestSummary:
    if not points:
        raise ValueError("at least one backtest point is required")
    errors = [point.predicted_move - point.actual_move for point in points]
    accuracy = mean(1.0 if point.direction_correct else 0.0 for point in points)
    confidence = mean(point.confidence for point in points)
    return LiveBacktestSummary(
        samples=len(points),
        directional_accuracy=float(accuracy),
        mean_absolute_error=float(mean(abs(error) for error in errors)),
        root_mean_squared_error=float(sqrt(mean(error * error for error in errors))),
        mean_bias=float(mean(errors)),
        mean_confidence=float(confidence),
        calibration_gap=float(confidence - accuracy),
    )


def summarize_by_regime(points: Sequence[LiveBacktestPoint]) -> dict[str, LiveBacktestSummary]:
    regimes = sorted({point.regime for point in points})
    return {
        regime: summarize_live_backtest([point for point in points if point.regime == regime])
        for regime in regimes
    }
