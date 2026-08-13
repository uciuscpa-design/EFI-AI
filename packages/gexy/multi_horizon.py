from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .live_prediction import LivePrediction, predict_live
from .surface_features import GEXSurfaceFeatures

DEFAULT_HORIZONS: tuple[int, ...] = (5, 15, 30, 60)


@dataclass(frozen=True)
class MultiHorizonPrediction:
    predictions: tuple[LivePrediction, ...]

    def by_horizon(self) -> dict[int, LivePrediction]:
        return {prediction.horizon_minutes: prediction for prediction in self.predictions}


def predict_multi_horizon(
    features: GEXSurfaceFeatures,
    *,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
) -> MultiHorizonPrediction:
    ordered: list[int] = []
    seen: set[int] = set()
    for horizon in horizons:
        value = int(horizon)
        if value <= 0:
            raise ValueError("horizons must be positive")
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    if not ordered:
        raise ValueError("at least one horizon is required")

    return MultiHorizonPrediction(
        predictions=tuple(
            predict_live(features, horizon_minutes=horizon)
            for horizon in ordered
        )
    )
