# GEXY opening-window validation batch 4 upstream cost plan

## Status

Recorded after the frozen batch-4 protocol and before any batch-4 endpoint inspection.

Frozen dates remain, in acquisition order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

The initial pricing-only planner displayed dates chronologically because the earlier multi-date parser sorted input. That display ordering did not expose endpoint data and did not alter the frozen validation-date set. The parser was changed before paid acquisition to preserve first-seen caller order while de-duplicating dates, with a regression test covering the frozen batch-4 order.

## Initial metadata-only pricing result

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Initial chain status |
|---|---:|---:|---:|---|
| 2026-08-03 | $0.032331 | $0.012128 | $0.044459 | missing |
| 2026-07-31 | $0.032616 | $0.012515 | $0.045131 | missing |
| 2026-07-30 | $0.032830 | $0.012203 | $0.045033 | missing |

**Estimated definition + OI total for all three dates: $0.134623.**

The default pricing run downloaded no market data.

## Safety change before paid chain build

`scripts/gexy_multiday_plan.py` was hardened before paid chain acquisition. `--build-missing-chains` defaults to a zero-dollar fail-closed guard unless `--max-metadata-download-cost` is explicitly supplied. Before downloading any missing-chain definition/OI data, the script re-prices every missing date in the invocation and aborts before download if the re-priced total exceeds the reviewed guard.

The guard is a local preflight estimate guard, not a vendor transactional billing cap. Full-day CBBO is a separate acquisition stage with its own preflight cost guard.

## Reviewed paid metadata cap and completed chain acquisition

The reviewed batch-4 missing-chain metadata cap was **$0.15 total** for the frozen three-date invocation. Immediately before download, the script re-priced the same scope at exactly **$0.134623**, below the guard, and then acquired only the definition/statistics inputs needed to build the daily 0DTE chains.

Paid chain acquisition completed in the frozen order:

| Date | Re-priced metadata total | Contracts saved | Chain file |
|---|---:|---:|---|
| 2026-08-03 | $0.044459 | 492 | `gexy_spxw_2026-08-03_0dte_oi.csv` |
| 2026-07-31 | $0.045131 | 958 | `gexy_spxw_2026-07-31_0dte_oi.csv` |
| 2026-07-30 | $0.045033 | 474 | `gexy_spxw_2026-07-30_0dte_oi.csv` |

**Total pre-download estimated metadata spend used for the guard: $0.134623.** No CBBO or TCBBO records were downloaded in this stage.

## Exact-symbol full-day CBBO-1m pricing after chain build

Once the chains existed, the same run metadata-priced the exact-symbol full-day CBBO-1m scope without downloading those quotes:

| Date | Contracts | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---:|
| 2026-08-03 | 492 | $0.026307 |
| 2026-07-31 | 958 | $0.050464 |
| 2026-07-30 | 474 | $0.025125 |

**Estimated full-day CBBO-1m total: $0.101896.**

The combined metadata estimate plus priced-but-not-yet-downloaded CBBO estimate is $0.236519, but only the $0.134623 chain-input stage has been executed so far.

Opening-only +/-200 TCBBO pricing remains pending until replay features exist so the opening forward can be determined under the frozen selection rule.

## CBBO replay safety change and fresh no-download preflight

Before any CBBO purchase, `scripts/gexy_multiday_replay.py` was hardened to preserve first-seen date order, default `--max-new-cbbo-cost` to $0.00, and re-price every missing CBBO day immediately before the paid batch. If the re-priced total exceeds the explicit cap, the script aborts before download. The local regression test for the replay planner passed before the fresh preflight.

A fresh no-download replay preflight was then run in the frozen order and returned:

| Date | Contracts | Quotes cached | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-08-03 | 492 | no | $0.026307 |
| 2026-07-31 | 958 | no | $0.050464 |
| 2026-07-30 | 474 | no | $0.025125 |

**Fresh estimated new CBBO total: $0.101896.** The displayed cost guard was $0.000000 and the script exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap

The reviewed Batch-4 full-day exact-symbol CBBO-1m cap is **$0.12 total** for the frozen three-date invocation. This provides $0.018104 of estimate headroom over the fresh $0.101896 preflight.

The paid CBBO replay acquisition is authorized only if the immediate pre-download re-priced total is at or below $0.12. If it exceeds $0.12, the script must abort before download and no higher cap should be substituted without a new recorded review.

This authorization covers only the exact-symbol full-day CBBO-1m data needed to generate the replay caches for 2026-08-03, 2026-07-31, and 2026-07-30. It does **not** authorize opening-window TCBBO or any other market-data purchase.

No batch-4 endpoint has been inspected.
