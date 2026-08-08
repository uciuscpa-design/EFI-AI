# EFI-AI deployment on FastAPI Cloud

## Recommended production path

Deploy the FastAPI application to FastAPI Cloud with a managed PostgreSQL database. Keep `EFI_PAPER_TRADING=true` during the entire initial production rollout.

### Required environment variables

- `EFI_ENVIRONMENT=production`
- `EFI_PAPER_TRADING=true`
- `EFI_DATABASE_URL=<managed PostgreSQL connection string>`
- `EFI_API_KEY=<random production secret>`
- `EFI_MAX_POSITION_NOTIONAL=<approved limit>`
- `EFI_MAX_DAILY_LOSS=<approved limit>`

### Release procedure

1. Connect the GitHub repository to FastAPI Cloud.
2. Select `main` as the production branch.
3. Configure the environment variables as platform secrets.
4. Deploy the application.
5. Run `alembic upgrade head` as the release migration step before traffic is served.
6. Verify `/health` and `/ready`.
7. Verify the paper-order workflow with a non-production test request.
8. Confirm logs contain request IDs and audit events.
9. Do not configure live brokerage credentials.

### Rollback

Rollback to the previous application revision through the hosting platform. Database migrations must be backward-compatible before schema changes are released.

### Production gate

A release is not considered live-ready until health, readiness, database connectivity, authentication, audit logging, and paper execution have all been verified.
