from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from packages.gexy.live_prediction import PRODUCTION_HORIZONS_MINUTES
from packages.gexy.prediction_journal import PredictionJournalEntry, load_entries

ROOT = Path(__file__).resolve().parents[2]
UI_PATH = ROOT / "apps" / "gexy_ui" / "index.html"
LIVE_JOURNAL = ROOT / "data" / "gexy" / "live_predictions.jsonl"
SHADOW_JOURNAL = ROOT / "data" / "gexy" / "shadow_predictions.jsonl"

app = FastAPI(title="GEXY Live Forecast API", version="1.0.0")


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


def _resolve_source(source: Literal["auto", "production", "shadow"], horizon: int) -> tuple[str, Path]:
    if source == "production":
        return "production", LIVE_JOURNAL
    if source == "shadow":
        return "shadow", SHADOW_JOURNAL
    if horizon in PRODUCTION_HORIZONS_MINUTES:
        return "production", LIVE_JOURNAL
    return "shadow", SHADOW_JOURNAL


def _entry_payload(entry: PredictionJournalEntry) -> dict[str, Any]:
    prediction = entry.prediction
    return {
        "prediction_id": entry.prediction_id,
        "timestamp": entry.created_at.isoformat(),
        "due_at": entry.due_at.isoformat(),
        "spot": entry.spot,
        "direction": prediction.direction,
        "expected_move_points": prediction.expected_move_points,
        "forecast_spot": entry.spot + prediction.expected_move_points,
        "primary_target": prediction.primary_target,
        "invalidation_level": prediction.invalidation_level,
        "confidence": prediction.confidence,
        "horizon_minutes": prediction.horizon_minutes,
        "regime": prediction.regime,
        "model_version": entry.model_version,
        "resolved": entry.resolved,
        "resolved_at": None if entry.resolved_at is None else entry.resolved_at.isoformat(),
        "realized_spot": entry.realized_spot,
        "realized_move_points": entry.realized_move_points,
        "directional_hit": entry.directional_hit,
        "absolute_error_points": entry.absolute_error_points,
    }


def _filtered_entries(path: Path, horizon: int) -> list[PredictionJournalEntry]:
    return [entry for entry in load_entries(path) if entry.prediction.horizon_minutes == horizon]


@app.get("/")
def operator_ui() -> FileResponse:
    if not UI_PATH.exists():
        raise HTTPException(status_code=404, detail="GEXY operator UI not found")
    return FileResponse(UI_PATH)


@app.get("/ui")
def operator_ui_alias() -> FileResponse:
    return operator_ui()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "gexy",
        "version": app.version,
        "production_journal_present": LIVE_JOURNAL.exists(),
        "shadow_journal_present": SHADOW_JOURNAL.exists(),
    }


@app.get("/v1/live/horizons")
def live_horizons() -> dict[str, Any]:
    return {
        "production": list(PRODUCTION_HORIZONS_MINUTES),
        "shadow": list(range(1, 61)),
        "minimum_minutes": 1,
        "maximum_minutes": 60,
        "step_minutes": 1,
    }


@app.get("/v1/live/history")
def live_history(
    horizon: int = Query(default=5, ge=1, le=60),
    source: Literal["auto", "production", "shadow"] = "auto",
    limit: int = Query(default=300, ge=1, le=2000),
) -> dict[str, Any]:
    resolved_source, path = _resolve_source(source, horizon)
    rows = _filtered_entries(path, horizon)
    selected = rows[-limit:]
    return {
        "source": resolved_source,
        "journal": str(path.relative_to(ROOT)),
        "horizon_minutes": horizon,
        "count": len(selected),
        "total_matching": len(rows),
        "points": [_entry_payload(entry) for entry in selected],
    }


@app.get("/v1/live/latest")
def live_latest(
    horizon: int = Query(default=5, ge=1, le=60),
    source: Literal["auto", "production", "shadow"] = "auto",
) -> dict[str, Any]:
    resolved_source, path = _resolve_source(source, horizon)
    rows = _filtered_entries(path, horizon)
    if not rows:
        raise HTTPException(status_code=404, detail=f"no {horizon}m GEXY predictions available")
    return {
        "source": resolved_source,
        "journal": str(path.relative_to(ROOT)),
        "data": _entry_payload(rows[-1]),
    }


@app.post("/v1/replay/forecast")
def replay_forecast(snapshot: ReplaySnapshot) -> dict[str, Any]:
    """Transport-contract endpoint retained for deterministic replay clients."""
    return {
        "timestamp": snapshot.timestamp,
        "spot": snapshot.spot,
        "forecasts": [],
        "status": "model_not_loaded",
    }
