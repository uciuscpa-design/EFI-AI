# GEXY opening-window validation Batch 6 cost plan

## Status

Recorded after the Batch-6 heterogeneity-replication protocol was frozen and after the first metadata-only upstream pricing run. No Batch-6 market data have been downloaded and no Batch-6 endpoint has been inspected.

Frozen dates and acquisition order remain:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

## Initial metadata-only chain-input pricing

The guarded multi-day planner was run without `--build-missing-chains`, so it used metadata cost estimation only and downloaded no market data.

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Chain status |
|---|---:|---:|---:|---|
| 2026-07-24 | $0.033182 | $0.012427 | $0.045609 | missing |
| 2026-07-23 | $0.032585 | $0.012616 | $0.045202 | missing |
| 2026-07-22 | $0.033088 | $0.012667 | $0.045756 | missing |

**Estimated Definition + OI total for all three frozen dates: $0.136567.**

Exact-symbol full-day CBBO-1m pricing remains pending until the three chain CSVs exist.

## Reviewed paid metadata cap

The reviewed Batch-6 missing-chain metadata cap is **$0.15 total** for the exact frozen three-date invocation. This provides $0.013433 of estimate headroom over the current $0.136567 estimate.

The paid chain-input request is authorized only if the downloader immediately re-prices the same three missing-chain Definition/OI inputs at or below $0.15 before any download. If the re-priced total exceeds $0.15, the script must abort before download and no higher cap may be substituted without a new recorded review.

This authorization covers only the Definition/statistics inputs required to build the three 0DTE chain CSVs. It does not authorize full-day CBBO-1m, opening-window TCBBO, or any other Batch-6 market-data purchase.

Acquisition must remain in frozen order: **2026-07-24 -> 2026-07-23 -> 2026-07-22**.

No Batch-6 endpoint may be extracted or inspected before all later authorized Batch-6 acquisitions and local preparation are complete.
