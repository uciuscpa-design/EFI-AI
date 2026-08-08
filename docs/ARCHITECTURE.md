# Architecture

EFI-AI is split into bounded layers:

- `apps/api`: HTTP boundary and request validation.
- `apps/web`: operator dashboard.
- `packages/core`: configuration, domain models, security and audit contracts.
- `packages/data`: market-data and broker boundaries.
- `packages/strategy`: deterministic strategy layer.
- `packages/risk`: pre-execution risk controls.
- `packages/persistence`: SQLAlchemy models and persistence services.
- `migrations`: Alembic database migrations.

The execution path is deliberately paper-only. A future live broker must implement an explicit interface behind authentication, risk approval, audit persistence, and a separately controlled feature flag.
