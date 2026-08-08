# Production readiness gate

## Application

- [x] FastAPI application
- [x] Health/readiness endpoints
- [x] Paper trading execution boundary
- [x] Risk controls
- [x] Audit event boundary
- [x] Request logging
- [x] Database migrations
- [x] CI tests

## Deployment

- [x] Docker/Compose configuration
- [x] PostgreSQL service configuration
- [x] Stack validation script
- [x] FastAPI Cloud deployment procedure
- [ ] Production hosting account connected
- [ ] Production PostgreSQL provisioned
- [ ] Production `EFI_API_KEY` provisioned
- [ ] Production deployment executed
- [ ] Post-deployment health/readiness verified

## Trading safety

- [x] `EFI_PAPER_TRADING=true` required for initial rollout
- [x] No live brokerage credentials in repository
- [ ] Independent operational approval for any future live execution

The unchecked deployment items require access to the selected hosting provider and production secrets; they cannot be truthfully marked complete from repository access alone.
