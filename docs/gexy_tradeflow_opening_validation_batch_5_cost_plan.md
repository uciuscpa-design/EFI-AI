# GEXY opening-window validation Batch 5 cost plan

## Status

Recorded after the Batch-5 protocol was frozen and before any Batch-5 endpoint inspection.

Frozen dates and acquisition order remain:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

## Initial metadata-only chain-input pricing

The guarded multi-day planner was first run without `--build-missing-chains`, so it called metadata pricing only and downloaded no market data.

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Initial chain status |
|---|---:|---:|---:|---|
| 2026-07-29 | $0.032019 | $0.012375 | $0.044394 | missing |
| 2026-07-28 | $0.032458 | $0.012505 | $0.044963 | missing |
| 2026-07-27 | $0.032790 | $0.012561 | $0.045351 | missing |

**Estimated Definition + OI total for all three frozen dates: $0.134707.**

## Reviewed paid metadata cap and completed chain acquisition

The reviewed Batch-5 missing-chain metadata cap was **$0.15 total** for the exact frozen three-date invocation. Immediately before download, the planner re-priced the same Definition/OI scope at **$0.134707**, below the guard, and then acquired only the definition/statistics inputs required to build the 0DTE chains.

Acquisition completed in frozen order:

| Date | Re-priced metadata total | Contracts saved | Chain file |
|---|---:|---:|---|
| 2026-07-29 | $0.044394 | 488 | `gexy_spxw_2026-07-29_0dte_oi.csv` |
| 2026-07-28 | $0.044963 | 488 | `gexy_spxw_2026-07-28_0dte_oi.csv` |
| 2026-07-27 | $0.045351 | 488 | `gexy_spxw_2026-07-27_0dte_oi.csv` |

**Total pre-download estimated metadata spend used for the guard: $0.134707.** The guard is a local preflight estimate guard, not a vendor transactional billing cap.

No full-day CBBO-1m or opening-window TCBBO records were downloaded in this stage.

## Exact-symbol full-day CBBO-1m pricing after chain build

After the chains were built, the same run metadata-priced the exact-symbol full-day CBBO-1m replay scope without downloading those quotes:

| Date | Contracts | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---:|
| 2026-07-29 | 488 | $0.027188 |
| 2026-07-28 | 488 | $0.026953 |
| 2026-07-27 | 488 | $0.026458 |

**Estimated exact-symbol full-day CBBO-1m total: $0.080599.**

The combined metadata estimate plus currently priced CBBO estimate is **$0.215307**. Only the $0.134707 chain-input stage has been executed so far; the CBBO figure is pricing-only.

## Next rule

Before any paid CBBO acquisition, run the guarded multi-day replay planner in no-download mode for the same three frozen dates and 15-minute horizon. Record the fresh exact-symbol CBBO estimate and confirm the downloader remains fail-closed at a zero-dollar guard.

Only after that fresh no-download preflight may a separate reviewed CBBO cap be recorded. No opening-window TCBBO purchase is authorized yet.

No Batch-5 endpoint may be extracted or inspected before all later authorized Batch-5 acquisitions and local preparation are complete.
