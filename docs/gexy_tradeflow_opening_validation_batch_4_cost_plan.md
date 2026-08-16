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

## CBBO replay safety change and fresh no-download preflight

Before any CBBO purchase, `scripts/gexy_multiday_replay.py` was hardened to preserve first-seen date order, default `--max-new-cbbo-cost` to $0.00, and re-price every missing CBBO day immediately before the paid batch. If the re-priced total exceeds the explicit cap, the script aborts before download. The local regression test for the replay planner passed before the fresh preflight.

A fresh no-download replay preflight was then run in the frozen order and returned:

| Date | Contracts | Quotes cached | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-08-03 | 492 | no | $0.026307 |
| 2026-07-31 | 958 | no | $0.050464 |
| 2026-07-30 | 474 | no | $0.025125 |

**Fresh estimated new CBBO total: $0.101896.** The displayed cost guard was $0.000000 and the script exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap and completed replay acquisition

The reviewed Batch-4 full-day exact-symbol CBBO-1m cap was **$0.12 total** for the frozen three-date invocation, providing $0.018104 of estimate headroom over the fresh $0.101896 preflight.

Immediately before the paid acquisition, the missing CBBO scope was re-priced at **$0.101896**, below the $0.12 guard. Acquisition then completed for all three frozen dates and produced the corresponding full-day CBBO cache and replay feature CSV for each date. The final multi-day replay summary reported:

- dates completed: 3
- re-priced new CBBO estimate used for guard: **$0.101896**
- manifest: `gexy_spxw_multiday_replay_manifest.csv`
- all three replay sessions were generated before any opening-window TCBBO endpoint data were acquired or inspected.

For 2026-07-30, the terminal output additionally showed 389 replay minutes, no low-parity-pair skips, median Greeks solved 237 / 80.3%, first forward 7377.481 and last forward 7438.882. These replay diagnostics are upstream state construction and do not expose the batch-4 trade-flow endpoint.

The cumulative pre-download estimates used for authorized Batch-4 upstream acquisition so far are **$0.134623 metadata + $0.101896 CBBO = $0.236519**. This is a sum of local preflight estimates, not a claim about final vendor billing.

## Next stage: opening-only bounded TCBBO pricing

The replay caches now provide the frozen opening-forward anchor needed to select SPXW 0DTE contracts within +/-200 SPX points. The next permitted operation is metadata-only pricing of **TCBBO**, **09:30-10:00 America/New_York only**, **opening-forward +/-200 points**, for the same three frozen dates.

No opening TCBBO purchase is authorized by this document yet. The bounded TCBBO total must be priced and reviewed separately before any paid TCBBO command.

No batch-4 endpoint has been inspected.
