from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

from packages.gexy.dataset import ResearchRow
from packages.gexy.live import generate_forecast
from .models import ModelRegistry


async def forecast_stream(
    snapshots: AsyncIterator[ResearchRow],
    registry: ModelRegistry,
    *,
    sleep_seconds: float = 0.0,
) -> AsyncIterator[str]:
    """Emit newline-delimited JSON forecast events from replay/live snapshots."""
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be non-negative")
    async for snapshot in snapshots:
        bundle = registry.current()
        forecast = generate_forecast(snapshot, dict(bundle.models))
        payload: dict[str, Any] = {
            "type": "gexy.forecast",
            "model_version": bundle.version,
            "trained_through": bundle.trained_through.isoformat(),
            "data": {
                "timestamp": forecast.timestamp.isoformat(),
                "spot": forecast.spot,
                "forecasts": [f.__dict__ for f in forecast.forecasts],
            },
        }
        yield json.dumps(payload, default=str)
        if sleep_seconds:
            await asyncio.sleep(sleep_seconds)
