# EFI-AI

EFI-AI is a production-oriented AI trading assistant foundation. The initial repository is organized into six bounded components with a safety-first default: market analysis and portfolio workflows are paper-trading only until live execution is explicitly implemented and enabled.

## Repository structure

```text
apps/
  api/          # FastAPI HTTP service
  web/          # lightweight operator dashboard
packages/
  core/         # domain models and configuration
  data/         # market-data interfaces and in-memory implementation
  strategy/     # signal generation and portfolio decisions
  risk/         # position sizing and risk guardrails
infra/
  docker/       # container assets
  compose/      # local orchestration
scripts/        # developer and deployment helpers
tests/          # automated tests
```

## Initial production baseline

- Python 3.12
- FastAPI + Uvicorn
- Pydantic settings
- Deterministic paper-trading domain interfaces
- Explicit risk limits before order creation
- Docker and Compose deployment assets
- Health/readiness endpoints
- Unit tests for core and risk behavior

## Safety

Live brokerage execution is intentionally not included in this baseline. The execution boundary is represented by a paper broker interface so that real-money integration can be added behind explicit controls, authentication, auditing, and additional tests.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e '.[dev]'
uvicorn apps.api.main:app --reload
```

API documentation is available at `/docs` when the service is running.

## Test

```bash
pytest
```
