from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="GEXY Live Forecast API", version="0.1.0")


class ReplaySnapshot(BaseModel):
    timestamp: datetime
    spot: float = Field(gt=0)
    spot_change: float = 0.0
    iv_change: float = 0.0
    total_gex: float = 0.0
    gamma_change: float = 0.0
    vanna_component: float = 0.0
    charm_component: float = 0.0
    estimated_hedge_demand: float = 0.0
    positioning_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gexy"}


@app.post("/v1/replay/forecast")
def replay_forecast(snapshot: ReplaySnapshot) -> dict[str, Any]:
    """Replay endpoint used to exercise the live API before a vendor feed is connected."""
    # The endpoint deliberately exposes the transport contract first. Model loading
    # is injected in the deployment layer rather than training on request data.
    return {
        "timestamp": snapshot.timestamp,
        "spot": snapshot.spot,
        "forecasts": [],
        "status": "model_not_loaded",
    }
