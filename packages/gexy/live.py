from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .model import LinearModel, predict
from .dataset import ResearchRow


@dataclass(frozen=True)
class HorizonForecast:
    horizon_minutes: int
    timestamp: datetime
    spot: float
    predicted_move_points: float
    up_probability: float
    confidence: float


@dataclass(frozen=True)
class LiveForecast:
    timestamp: datetime
    spot: float
    forecasts: tuple[HorizonForecast, ...]


def generate_forecast(
    row: ResearchRow,
    models: dict[int, LinearModel],
) -> LiveForecast:
    """Generate forecasts from pre-fitted, horizon-specific models.

    Models must be fitted before entering the live path. This function performs
    no training and has no access to future observations.
    """
    forecasts: list[HorizonForecast] = []
    for horizon, model in sorted(models.items()):
        prediction = predict(model, row)
        confidence = abs(prediction.up_probability - 0.5) * 2.0
        forecasts.append(
            HorizonForecast(
                horizon_minutes=horizon,
                timestamp=row.timestamp,
                spot=row.spot,
                predicted_move_points=prediction.move_points,
                up_probability=prediction.up_probability,
                confidence=confidence,
            )
        )
    return LiveForecast(row.timestamp, row.spot, tuple(forecasts))
