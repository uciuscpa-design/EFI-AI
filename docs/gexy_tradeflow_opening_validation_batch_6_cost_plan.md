# GEXY opening-window validation Batch 6 cost plan

## Status

Recorded after the Batch-6 heterogeneity-replication protocol was frozen and before any Batch-6 endpoint inspection.

Frozen dates and acquisition order remain:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

## Initial metadata-only chain-input pricing

The guarded multi-day planner was first run without `--build-missing-chains`, so it used metadata cost estimation only and downloaded no market data.

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Initial chain status |
|---|---:|---:|---:|---|
| 2026-07-24 | $0.033182 | $0.012427 | $0.045609 | missing |
| 2026-07-23 | $0.032585 | $0.012616 | $0.045202 | missing |
| 2026-07-22 | $0.033088 | $0.012667 | $0.045756 | missing |

**Estimated Definition + OI total for all three frozen dates: $0.136567.**

## Reviewed paid metadata cap and completed chain acquisition

The reviewed Batch-6 missing-chain metadata cap was **$0.15 total** for the exact frozen three-date invocation. Immediately before download, the planner re-priced the same Definition/OI scope at **$0.136567**, below the guard, and then acquired only the definition/statistics inputs required to build the 0DTE chains.

Acquisition completed in frozen order:

| Date | Re-priced metadata total | Contracts saved | Chain file |
|---|---:|---:|---|
| 2026-07-24 | $0.045609 | 618 | `gexy_spxw_2026-07-24_0dte_oi.csv` |
| 2026-07-23 | $0.045202 | 484 | `gexy_spxw_2026-07-23_0dte_oi.csv` |
| 2026-07-22 | $0.045756 | 496 | `gexy_spxw_2026-07-22_0dte_oi.csv` |

**Total pre-download estimated metadata spend used for the guard: $0.136567.** The guard is a local preflight estimate guard, not a vendor transactional billing cap.

No full-day CBBO-1m or opening-window TCBBO records were downloaded in this stage.

## Exact-symbol full-day CBBO-1m pricing after chain build

After the chains were built, the same run metadata-priced the exact-symbol full-day CBBO-1m replay scope without downloading those quotes:

| Date | Contracts | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---:|
| 2026-07-24 | 618 | $0.033803 |
| 2026-07-23 | 484 | $0.025698 |
| 2026-07-22 | 496 | $0.024953 |

**Estimated exact-symbol full-day CBBO-1m total: $0.084454.**

The combined metadata estimate plus currently priced CBBO estimate is **$0.221021**. Only the $0.136567 chain-input stage has been executed so far; the CBBO figure remains pricing-only.

## Next rule

Before any paid CBBO acquisition, run the guarded multi-day replay planner in no-download mode for the same three frozen dates and 15-minute horizon. Record the fresh exact-symbol CBBO estimate and confirm the downloader remains fail-closed at a zero-dollar guard.

Only after that fresh no-download preflight may a separate reviewed CBBO cap be recorded. No opening-window TCBBO purchase is authorized yet.

No Batch-6 endpoint may be extracted or inspected before all later authorized acquisitions and local preparation are complete.
