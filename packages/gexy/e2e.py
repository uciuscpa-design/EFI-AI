from __future__ import annotations

import json
from collections.abc import AsyncIterator

from .live import generate_forecast
from .live_bridge import snapshot_to_row
from .market_adapter import MarketSnapshot
from apps.gexy_api.models import ModelRegistry


async def replay_forecast_events(
    snapshots: AsyncIterator[MarketSnapshot],
    registry: ModelRegistry,
) -> AsyncIterator[str]:
    """Run normalized replay data through features and pre-fitted models."""
    previous_spot = 0.0
    previous_iv = None
    async for snapshot in snapshots:
        row = snapshot_to_row(snapshot, previous_spot=previous_spot, previous_iv=previous_iv)
        bundle = registry.current()
        forecast = generate_forecast(row, dict(bundle.models))
        event = {
            "type": "gexy.forecast",
            "model_version": bundle.version,
            "trained_through": bundle.trained_through.isoformat(),
            "data": {
                "timestamp": forecast.timestamp.isoformat(),
                "spot": forecast.spot,
                "forecasts": [f.__dict__ for f in forecast.forecasts],
            },
        }
        yield json.dumps(event, default=str)
        previous_spot = snapshot.spot
        previous_iv = snapshot.iv
