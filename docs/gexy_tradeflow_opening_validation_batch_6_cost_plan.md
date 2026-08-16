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

The cumulative pre-download estimate used for authorized Batch-6 upstream acquisition before TCBBO is **$0.136567 metadata + $0.084454 CBBO = $0.221021**. This is estimate-based budget accounting, not final vendor billing.

## Opening-only bounded TCBBO pricing

After all three replay caches were complete, the trade-flow cost planner was run in metadata-only mode for the exact frozen Batch-6 scope: SPXW 0DTE, schema `tcbbo`, 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, and the three dates in frozen order. No TCBBO records were downloaded.

| Date | Opening forward | Selected contracts | Opening TCBBO estimate |
|---|---:|---:|---:|
| 2026-07-24 | 7411.862708 | 160 | $2.076316 |
| 2026-07-23 | 7416.675000 | 160 | $2.356086 |
| 2026-07-22 | 7494.025000 | 160 | $1.901407 |

**Estimated bounded opening-only TCBBO total: $6.333809.**

## Reviewed paid TCBBO caps and completed acquisition

The reviewed per-date preflight-estimate caps were:

| Date | Estimate | Reviewed cap | Immediate recheck | Result |
|---|---:|---:|---:|---|
| 2026-07-24 | $2.076316 | $2.14 | $2.076316 | acquired |
| 2026-07-23 | $2.356086 | $2.43 | $2.356086 | acquired |
| 2026-07-22 | $1.901407 | $1.96 | $1.901407 | acquired |

All three immediate pre-download rechecks stayed within their recorded caps, and acquisition completed in the frozen order **2026-07-24 -> 2026-07-23 -> 2026-07-22**. The cached raw files are:

- `data/gexy/tradeflow/gexy_spxw_2026-07-24_0930_1000_tcbbo.dbn.zst`
- `data/gexy/tradeflow/gexy_spxw_2026-07-23_0930_1000_tcbbo.dbn.zst`
- `data/gexy/tradeflow/gexy_spxw_2026-07-22_0930_1000_tcbbo.dbn.zst`

The summed TCBBO pre-download estimate was **$6.333809**. Combined with the earlier Definition/OI and CBBO estimate guards, cumulative Batch-6 estimate-based acquisition accounting is **$6.554830**. These values are pre-download estimates/guards rather than final vendor billing.

No Batch-6 endpoint was inspected during acquisition. No further paid market-data request is required before the Batch-6 local preparation and one-time frozen reveal.

## Next rule

All remaining work before the primary Batch-6 reveal must be local-only. Run a Batch-6-specific preparation wrapper across all three frozen dates before the dedicated 15-minute validator. The preparation wrapper must not compute or display Endpoint A or Endpoint B. No date-by-date endpoint inspection is permitted before the one-time full three-date reveal.
