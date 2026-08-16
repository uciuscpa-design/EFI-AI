# GEXY temporal-extension holdout cost plan

## Status

This cost plan is governed by the separately frozen temporal-extension holdout protocol. The three reserved dates remain a temporal-extension holdout and are not being used to rescue the failed 09:40 session-state screen.

Reserved holdout dates, in frozen order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

No endpoint value may be inspected until all frozen holdout acquisition/preparation stages are complete and the dedicated holdout reveal is ready.

## Stage 1 — definition + OI chain inputs

Initial metadata-only estimates:

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate |
|---|---:|---:|---:|
| 2026-07-21 | $0.033219 | $0.012674 | $0.045893 |
| 2026-07-20 | $0.033226 | $0.012015 | $0.045241 |
| 2026-07-17 | $0.032428 | $0.012373 | $0.044801 |

Exact estimated definition+OI total: **$0.135936**.

Reviewed Stage-1 guard: **$0.15 total**.

Executed paid command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-07-21,2026-07-20,2026-07-17 --build-missing-chains --max-metadata-download-cost 0.15
```

Immediate preflight re-price remained **$0.135936**, below the $0.15 guard, so the definition/statistics requests proceeded.

Stage-1 outputs:

| Date | Chain contracts | Chain status |
|---|---:|---|
| 2026-07-21 | 490 | built |
| 2026-07-20 | 474 | built |
| 2026-07-17 | 1018 | built |

The planner explicitly reported that Stage 1 downloaded definition/statistics data only. Full-day CBBO quotes were **not** downloaded in this stage.

## Stage 2 — exact-symbol full-day CBBO

With all three cached chains available, the exact-symbol 09:30-16:00 America/New_York CBBO-1m estimates are:

| Date | Contracts | Exact-symbol CBBO-1m estimate |
|---|---:|---:|
| 2026-07-21 | 490 | $0.024306 |
| 2026-07-20 | 474 | $0.026450 |
| 2026-07-17 | 1018 | $0.054968 |

Exact Stage-2 CBBO total estimate: **$0.105724**.

Estimated cumulative Stage-1 + Stage-2 data cost: **$0.241660**.

### Reviewed Stage-2 cap

Freeze a total new-CBBO guard of **$0.12** for the three dates combined.

This is a local fail-closed preflight estimate guard, not a vendor transactional billing cap. The replay driver must re-price all missing CBBO days immediately before any CBBO acquisition and abort if the re-priced total exceeds $0.12.

Authorized Stage-2 paid command only after explicit user execution:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_replay.py --dates 2026-07-21,2026-07-20,2026-07-17 --download --max-new-cbbo-cost 0.12
```

The replay driver may reuse any already-cached CBBO day at $0 new CBBO cost. For missing quote days it must use exact chain symbols only and the frozen 09:30-16:00 CBBO-1m scope.

The replay-generated state/features are preparation artifacts only. Do not inspect or adjudicate the temporal-extension Endpoint-B holdout result yet.

## Stage 3 — opening TCBBO tradeflow

Opening TCBBO acquisition remains **not yet authorized**.

After Stage 2 succeeds:

1. retain the cached CBBO/replay state locally;
2. price the exact frozen opening-window TCBBO scope for the three holdout dates using metadata-only planning;
3. record the exact per-date estimates;
4. freeze separate reviewed TCBBO caps before any paid TCBBO request;
5. acquire/extract/build tradeflow features without revealing the holdout Endpoint B;
6. run the dedicated frozen holdout reveal only after all preparation is complete.

## Scientific and cost limits

The three dates remain an untouched temporal-extension holdout with respect to the endpoint result. Acquisition order, construction, opening window, 15-minute horizon, 90% Greek-volume coverage floor, hedge sign convention, and Endpoint-B definition remain governed by the frozen holdout protocol.

Paid requests require explicit reviewed caps and user execution. Re-running already-cached local stages must not trigger new downloads.
