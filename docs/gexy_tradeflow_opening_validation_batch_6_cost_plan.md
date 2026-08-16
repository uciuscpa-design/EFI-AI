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

## Exact-symbol full-day CBBO-1m pricing after chain build

After the chains were built, the same run metadata-priced the exact-symbol full-day CBBO-1m replay scope without downloading those quotes:

| Date | Contracts | Exact-symbol full-day CBBO-1m estimate |
|---|---:|---:|
| 2026-07-24 | 618 | $0.033803 |
| 2026-07-23 | 484 | $0.025698 |
| 2026-07-22 | 496 | $0.024953 |

**Estimated exact-symbol full-day CBBO-1m total: $0.084454.**

## Fresh no-download CBBO replay preflight

The guarded multi-day replay planner was then run for the same frozen three-date order with `--horizons 15` and without `--download`.

| Date | Contracts | Quotes cached | Fresh exact-symbol full-day CBBO-1m estimate |
|---|---:|---|---:|
| 2026-07-24 | 618 | no | $0.033803 |
| 2026-07-23 | 484 | no | $0.025698 |
| 2026-07-22 | 496 | no | $0.024953 |

**Fresh estimated new CBBO total: $0.084454.** The displayed cost guard was **$0.000000**, and the planner exited with `NO MARKET DATA DOWNLOADED`, confirming fail-closed behavior.

## Reviewed paid CBBO cap and completed replay acquisition

The reviewed Batch-6 full-day exact-symbol CBBO-1m cap was **$0.10 total** for the frozen three-date invocation, providing $0.015546 of estimate headroom over the fresh $0.084454 preflight.

Immediately before the paid replay acquisition, the missing CBBO scope was re-priced at **$0.084454**, below the $0.10 guard. The acquisition then completed across the full frozen three-date block and built the cached full-day CBBO files plus 15-minute replay feature files. The final multi-day summary reported:

- `MULTI-DAY REPLAY COMPLETE`
- `DATES: 3`
- `RE-PRICED NEW CBBO COST USED FOR GUARD: $0.084454`
- manifest: `gexy_spxw_multiday_replay_manifest.csv`

The visible replay diagnostics include successful feature generation for 2026-07-23 and 2026-07-22. For 2026-07-22, 385 replay minutes were built with 4 low-parity-pair minutes skipped; for 2026-07-23, the replay reported zero low-parity-pair minutes skipped. These are upstream construction diagnostics only and do not expose the Batch-6 trade-flow endpoints.

The cumulative pre-download estimate used for authorized Batch-6 upstream acquisition before TCBBO is **$0.136567 metadata + $0.084454 CBBO = $0.221021**. This is estimate-based budget accounting, not final vendor billing.

## Opening-only bounded TCBBO pricing

After all three replay caches were complete, the trade-flow cost planner was run in metadata-only mode for the exact frozen Batch-6 scope: SPXW 0DTE, schema `tcbbo`, 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, and the three dates in frozen order. No TCBBO records were downloaded.

| Date | Opening forward | Selected contracts | Opening TCBBO estimate |
|---|---:|---:|---:|
| 2026-07-24 | 7411.862708 | 160 | $2.076316 |
| 2026-07-23 | 7416.675000 | 160 | $2.356086 |
| 2026-07-22 | 7494.025000 | 160 | $1.901407 |

**Estimated bounded opening-only TCBBO total: $6.333809.**

The planner confirmed all three chains were cached, the frozen order was preserved, the window was 09:30-10:00 only, the strike scope was opening-forward +/-200 points, and the pricing run called metadata cost estimation only. No Batch-6 endpoint was extracted or inspected.

## Reviewed paid TCBBO caps

The per-date downloader remains fail-closed with an immediate re-price before any paid request and a hard local ceiling of $5.00 per invocation. To keep the requests tightly bounded while allowing modest pricing headroom, the reviewed per-date preflight-estimate caps are:

| Date | Current estimate | Reviewed cap | Estimate headroom |
|---|---:|---:|---:|
| 2026-07-24 | $2.076316 | **$2.14** | $0.063684 |
| 2026-07-23 | $2.356086 | **$2.43** | $0.073914 |
| 2026-07-22 | $1.901407 | **$1.96** | $0.058593 |

The sum of the reviewed per-date caps is **$6.53**, compared with the current three-date estimate of **$6.333809**.

Each paid request is authorized only if its immediate pre-download re-price is at or below that date's recorded cap. If any date exceeds its cap, stop before download and review the changed price rather than raising the cap automatically.

Acquisition must remain in frozen order: **2026-07-24 -> 2026-07-23 -> 2026-07-22**. This authorization covers only opening-window TCBBO for the frozen 09:30-10:00, +/-200-point scope. It does not authorize closing-window data, any alternate strike band, or any endpoint inspection between dates.

No Batch-6 endpoint may be extracted or inspected until all three authorized TCBBO acquisitions are complete and all three dates have gone through the frozen local preparation pipeline.
