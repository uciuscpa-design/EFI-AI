# GEXY opening-window validation Batch 5 cost plan

## Status

Recorded after the Batch-5 protocol was frozen and after the first metadata-only upstream pricing run. No Batch-5 market data have been downloaded and no Batch-5 endpoint has been inspected.

Frozen dates and acquisition order remain:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

## Initial metadata-only chain-input pricing

The guarded multi-day planner was run without `--build-missing-chains`, so it called metadata pricing only and downloaded no market data.

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Chain status |
|---|---:|---:|---:|---|
| 2026-07-29 | $0.032019 | $0.012375 | $0.044394 | missing |
| 2026-07-28 | $0.032458 | $0.012505 | $0.044963 | missing |
| 2026-07-27 | $0.032790 | $0.012561 | $0.045351 | missing |

**Estimated Definition + OI total for all three frozen dates: $0.134707.**

Exact-symbol full-day CBBO-1m pricing remains pending until the three chain CSVs exist.

## Reviewed paid metadata cap

The reviewed Batch-5 missing-chain metadata cap is **$0.15 total** for the exact frozen three-date invocation. This provides $0.015293 of estimate headroom over the current $0.134707 estimate.

The paid chain-input request is authorized only if the downloader immediately re-prices the same three missing-chain Definition/OI inputs at or below $0.15 before any download. If the re-priced total exceeds $0.15, the script must abort before download and no higher cap may be substituted without a new recorded review.

This authorization covers only the Definition/statistics inputs required to build the three 0DTE chain CSVs. It does not authorize full-day CBBO-1m, opening-window TCBBO, or any other Batch-5 market-data purchase.

Acquisition must remain in frozen order: **2026-07-29 -> 2026-07-28 -> 2026-07-27**.

No Batch-5 endpoint may be extracted or inspected before all later authorized Batch-5 acquisitions and local preparation are complete.
