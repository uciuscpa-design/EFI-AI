# GEXY temporal-extension holdout cost plan

## Status

This cost plan is frozen after the temporal-extension holdout protocol was recorded and after the first metadata-only cost-estimate pass, but before any paid acquisition for the reserved untouched dates.

Reserved holdout dates, in frozen order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

The holdout purpose remains the separately frozen temporal-extension test. These dates are not being used to rescue the failed 09:40 session-state screen.

## Stage 1 — definition + OI chain inputs

Metadata-only planner command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-07-21,2026-07-20,2026-07-17
```

Observed metadata estimates:

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Chain status |
|---|---:|---:|---:|---|
| 2026-07-21 | $0.033219 | $0.012674 | $0.045893 | missing |
| 2026-07-20 | $0.033226 | $0.012015 | $0.045241 | missing |
| 2026-07-17 | $0.032428 | $0.012373 | $0.044801 | missing |

Exact estimated definition+OI total: **$0.135936**.

The planner explicitly reported that this pass made metadata cost-estimate calls only and downloaded no market data.

## Reviewed Stage-1 cap

Freeze a total metadata-download guard of **$0.15** for all three dates combined.

This cap is intentionally tight relative to the exact estimate and is only a local fail-closed preflight guard. It is not a vendor transactional billing cap.

Authorized paid command only after explicit user execution:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-07-21,2026-07-20,2026-07-17 --build-missing-chains --max-metadata-download-cost 0.15
```

The command must re-price before download and abort if the re-priced total exceeds $0.15.

## Later stages are not yet authorized

Do not authorize or execute exact-symbol full-day CBBO downloads or opening TCBBO downloads yet.

After Stage 1 succeeds:

1. use the cached chains to obtain exact-symbol full-day CBBO metadata prices;
2. record those exact prices here;
3. freeze a separate reviewed CBBO cap before any paid CBBO request;
4. build replay state locally;
5. price the exact opening-window TCBBO scope;
6. freeze separate per-date TCBBO caps before any paid TCBBO request.

No endpoint value may be inspected until all frozen holdout acquisition/preparation stages are complete and the dedicated holdout reveal is ready.

## Scientific and cost limits

The three dates remain an untouched temporal-extension holdout. Acquisition order, construction, opening window, 15-minute horizon, 90% Greek-volume coverage floor, hedge sign convention, and Endpoint-B definition remain governed by the frozen holdout protocol.

Paid requests require explicit reviewed caps and user execution. Re-running already-cached local stages must not trigger new downloads.
