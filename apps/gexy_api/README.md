# GEXY API

Minimal FastAPI transport layer for GEXY live forecasts.

## Local run

From the repository root, install the project's FastAPI dependencies and run:

`uv run fastapi dev apps/gexy_api/main.py`

## Endpoints

- `GET /health`
- `POST /v1/replay/forecast`

The replay endpoint intentionally returns `model_not_loaded` until versioned fitted models are injected. This prevents a request from silently training or recalibrating a live model.

## Production next steps

1. Load versioned horizon models at startup.
2. Add normalized market-data adapters.
3. Add websocket/SSE streaming.
4. Persist forecast audit records.
5. Connect the frontend chart overlay.
