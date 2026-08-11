from __future__ import annotations

from dataclasses import dataclass
from math import log


@dataclass(frozen=True)
class ForecastLabel:
    horizon_minutes: int
    return_points: float
    direction_up: bool
    absolute_move_points: float


@dataclass(frozen=True)
class CalibrationMetrics:
    samples: int
    directional_accuracy: float
    mean_absolute_error: float
    mean_bias: float
    brier_score: float


def make_label(current_price: float, future_price: float, horizon_minutes: int) -> ForecastLabel:
    if current_price <= 0 or future_price <= 0:
        raise ValueError("prices must be positive")
    move = future_price - current_price
    return ForecastLabel(
        horizon_minutes=horizon_minutes,
        return_points=move,
        direction_up=move > 0,
        absolute_move_points=abs(move),
    )


def score_forecasts(
    predicted_up_probability: list[float],
    predicted_move_points: list[float],
    labels: list[ForecastLabel],
) -> CalibrationMetrics:
    if not (len(predicted_up_probability) == len(predicted_move_points) == len(labels)):
        raise ValueError("prediction and label lengths must match")
    n = len(labels)
    if n == 0:
        return CalibrationMetrics(0, 0.0, 0.0, 0.0, 0.0)
    for p in predicted_up_probability:
        if not 0 <= p <= 1:
            raise ValueError("probabilities must be in [0, 1]")
    correct = sum((p >= 0.5) == label.direction_up for p, label in zip(predicted_up_probability, labels))
    errors = [abs(pred - label.return_points) for pred, label in zip(predicted_move_points, labels)]
    biases = [pred - label.return_points for pred, label in zip(predicted_move_points, labels)]
    brier = sum((p - float(label.direction_up)) ** 2 for p, label in zip(predicted_up_probability, labels)) / n
    return CalibrationMetrics(
        samples=n,
        directional_accuracy=correct / n,
        mean_absolute_error=sum(errors) / n,
        mean_bias=sum(biases) / n,
        brier_score=brier,
    )
