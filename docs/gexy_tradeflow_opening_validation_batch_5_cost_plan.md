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

## Fresh no-download CBBO replay preflight

The guarded multi-day replay planner was then run for the same frozen three-date order with `--horizons 15` and without `--download`.

| Date | Contracts | Quotes cached | Fresh exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-07-29 | 488 | no | $0.027188 |
| 2026-07-28 | 488 | no | $0.026953 |
| 2026-07-27 | 488 | no | $0.026458 |

**Fresh estimated new CBBO total: $0.080599.** The displayed cost guard was **$0.000000**, and the planner exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap

The reviewed Batch-5 full-day exact-symbol CBBO-1m cap is **$0.10 total** for the frozen three-date invocation. This provides $0.019401 of estimate headroom over the fresh $0.080599 preflight.

The paid replay acquisition is authorized only if the immediate pre-download re-priced total is at or below **$0.10**. If the re-priced total exceeds $0.10, the script must abort before download and no higher cap may be substituted without a new recorded review.

This authorization covers only the exact-symbol full-day CBBO-1m data required to build replay caches for 2026-07-29, 2026-07-28, and 2026-07-27. It does not authorize opening-window TCBBO or any other Batch-5 market-data purchase.

After all three replay caches and 15-minute replay features are built, the next permitted paid-data-related operation is metadata-only pricing of the frozen opening 09:30-10:00, opening-forward +/-200 SPX-point TCBBO scope. No Batch-5 endpoint may be extracted or inspected before all later authorized acquisitions and local preparation are complete.
