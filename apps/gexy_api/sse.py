from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


async def _heartbeat_stream() -> AsyncIterator[str]:
    """Transport scaffold; real snapshots are injected by the market adapter."""
    while True:
        event = {
            "type": "gexy.status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "awaiting_market_adapter",
        }
        yield f"data: {json.dumps(event)}\n\n"
        await asyncio.sleep(5)


@router.get("/v1/stream")
async def stream() -> StreamingResponse:
    return StreamingResponse(
        _heartbeat_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
