from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .live import generate_forecast
from .model import LinearModel
from .dataset import ResearchRow


class ForecastService:
    def __init__(self, models: dict[int, LinearModel]) -> None:
        if not models:
            raise ValueError("at least one fitted model is required")
        self._models = dict(models)

    def forecast(self, row: ResearchRow) -> dict[str, Any]:
        result = generate_forecast(row, self._models)
        return asdict(result)
