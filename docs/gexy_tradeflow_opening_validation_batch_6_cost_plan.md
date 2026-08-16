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

## Fresh no-download CBBO replay preflight

The guarded multi-day replay planner was then run for the same frozen three-date order with `--horizons 15` and without `--download`.

| Date | Contracts | Quotes cached | Fresh exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-07-24 | 618 | no | $0.033803 |
| 2026-07-23 | 484 | no | $0.025698 |
| 2026-07-22 | 496 | no | $0.024953 |

**Fresh estimated new CBBO total: $0.084454.** The displayed cost guard was **$0.000000**, and the planner exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap

The reviewed Batch-6 full-day exact-symbol CBBO-1m cap is **$0.10 total** for the frozen three-date invocation. This provides $0.015546 of estimate headroom over the fresh $0.084454 preflight.

The paid replay acquisition is authorized only if the immediate pre-download re-priced total is at or below **$0.10**. If the re-priced total exceeds $0.10, the script must abort before download and no higher cap may be substituted without a new recorded review.

This authorization covers only the exact-symbol full-day CBBO-1m data required to build replay caches for 2026-07-24, 2026-07-23, and 2026-07-22. It does not authorize opening-window TCBBO or any other Batch-6 market-data purchase.

After all three replay caches and 15-minute replay features are built, the next permitted paid-data-related operation is metadata-only pricing of the frozen opening 09:30-10:00, opening-forward +/-200 SPX-point TCBBO scope. No Batch-6 endpoint may be extracted or inspected before all later authorized acquisitions and local preparation are complete.
