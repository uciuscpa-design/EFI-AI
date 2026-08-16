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

## Fresh no-download CBBO replay preflight

The guarded multi-day replay planner was then run for the same frozen three-date order with `--horizons 15` and without `--download`.

| Date | Contracts | Quotes cached | Fresh exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-07-29 | 488 | no | $0.027188 |
| 2026-07-28 | 488 | no | $0.026953 |
| 2026-07-27 | 488 | no | $0.026458 |

**Fresh estimated new CBBO total: $0.080599.** The displayed cost guard was **$0.000000**, and the planner exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap and completed replay acquisition

The reviewed Batch-5 full-day exact-symbol CBBO-1m cap was **$0.10 total** for the frozen three-date invocation, providing $0.019401 of estimate headroom over the fresh $0.080599 preflight.

Immediately before the paid replay acquisition, the missing CBBO scope was re-priced at **$0.080599**, below the $0.10 guard. The acquisition then completed for all three frozen dates and built the cached full-day CBBO files plus 15-minute replay feature files. The final multi-day replay summary reported:

- `DATES: 3`
- `RE-PRICED NEW CBBO COST USED FOR GUARD: $0.080599`
- manifest: `gexy_spxw_multiday_replay_manifest.csv`

The logged replay construction for 2026-07-28 and 2026-07-27 each produced 388 replay minutes with one low-parity-pair minute skipped. These are upstream replay diagnostics only and do not expose the Batch-5 trade-flow endpoints.

The cumulative pre-download estimate used for authorized Batch-5 upstream acquisition so far is **$0.134707 metadata + $0.080599 CBBO = $0.215306** (rounding differs by $0.000001 from the planner's previously displayed $0.215307 combined estimate). This is estimate-based budget accounting, not final vendor billing.

No opening-window TCBBO has been acquired and no Batch-5 endpoint has been inspected.

## Next rule

The replay caches now provide the opening-forward anchors needed for the frozen strike selection. The next permitted operation is **metadata-only pricing** of SPXW 0DTE TCBBO for the exact Batch-5 scope:

- dates in frozen order: 2026-07-29, 2026-07-28, 2026-07-27
- window: 09:30-10:00 America/New_York only
- strike band: opening-forward +/-200 SPX points
- schema: TCBBO

No TCBBO purchase is authorized yet. Record and review the per-date and total TCBBO estimates before setting any paid cap. No Batch-5 endpoint may be extracted or inspected before all later authorized acquisitions and local preparation are complete.
