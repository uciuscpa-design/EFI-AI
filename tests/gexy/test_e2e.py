from datetime import datetime, timezone

import pytest

from packages.gexy.e2e import replay_forecast_events
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot
from apps.gexy_api.models import ModelBundle, ModelRegistry


async def source():
    yield MarketSnapshot(
        datetime(2026, 8, 10, tzinfo=timezone.utc),
        6500,
        0.18,
        (OptionSnapshot("SPX", 6500, datetime(2026, 8, 14, tzinfo=timezone.utc), call_gamma=2, put_gamma=-1),),
    )


@pytest.mark.asyncio
async def test_replay_pipeline_requires_model_bundle():
    registry = ModelRegistry()
    with pytest.raises(RuntimeError):
        async for _ in replay_forecast_events(source(), registry):
            pass
