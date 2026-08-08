# EFI-AI deployment

## Local

```bash
cp .env.example .env
# Set EFI_POSTGRES_PASSWORD and EFI_API_KEY for protected deployments.
docker compose up --build
```

The API waits for PostgreSQL, applies `alembic upgrade head`, and then starts Uvicorn.

## Endpoints

- `GET /health` — process health; no authentication.
- `GET /ready` — database readiness and paper-trading state; no authentication.
- `POST /v1/market/quote` — authenticated when `EFI_API_KEY` is configured.
- `POST /v1/strategy/signal` — authenticated when `EFI_API_KEY` is configured.
- `POST /v1/orders/paper` — authenticated when `EFI_API_KEY` is configured.
- `GET /v1/audit/recent` — authenticated when `EFI_API_KEY` is configured.

## Safety

`EFI_PAPER_TRADING` remains `true` in the provided Compose configuration. No live brokerage adapter is included.
