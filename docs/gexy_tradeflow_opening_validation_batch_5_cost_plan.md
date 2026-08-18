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

## Opening-only bounded TCBBO pricing

After all three replay caches were complete, the trade-flow cost planner was run in metadata-only mode for the exact frozen Batch-5 scope: SPXW 0DTE, schema `tcbbo`, 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, and the three dates in frozen order. No TCBBO records were downloaded.

| Date | Opening forward | Selected contracts | Opening TCBBO estimate |
|---|---:|---:|---:|
| 2026-07-29 | 7418.484534 | 160 | $1.651881 |
| 2026-07-28 | 7412.995501 | 160 | $2.003905 |
| 2026-07-27 | 7470.111042 | 160 | $2.247783 |

**Estimated bounded opening-only TCBBO total: $5.903569.**

The planner confirmed all three chains were cached, the frozen order was preserved, the window was 09:30-10:00 only, the strike scope was opening-forward +/-200 points, and the pricing run called metadata cost estimation only. No Batch-5 endpoint was extracted or inspected.

## Reviewed paid TCBBO caps

The existing per-date TCBBO downloader remains fail-closed with an immediate exact re-price before any paid request and a hard local ceiling of $5.00 per invocation. To keep the authorized request tightly bounded while allowing modest pricing headroom, the reviewed per-date preflight-estimate caps are:

| Date | Current estimate | Reviewed cap | Estimate headroom |
|---|---:|---:|---:|
| 2026-07-29 | $1.651881 | **$1.70** | $0.048119 |
| 2026-07-28 | $2.003905 | **$2.07** | $0.066095 |
| 2026-07-27 | $2.247783 | **$2.32** | $0.072217 |

The sum of the reviewed per-date caps is **$6.09**, compared with the current three-date estimate of **$5.903569**.

Each paid request is authorized only if its immediate pre-download re-price is at or below that date's recorded cap. If any date exceeds its cap, stop before download and review the changed price rather than raising the cap automatically.

Acquisition must remain in frozen order: **2026-07-29 -> 2026-07-28 -> 2026-07-27**. This authorization covers only opening-window TCBBO for the frozen 09:30-10:00, +/-200-point scope. It does not authorize closing-window data, any alternate strike band, or any endpoint inspection between dates.

No Batch-5 endpoint may be extracted or inspected until all three authorized TCBBO acquisitions are complete and all three dates have gone through the frozen local preparation pipeline.