# GEXY opening-window validation batch 4 upstream cost plan

## Status

Recorded after the frozen batch-4 protocol and before any paid batch-4 market-data download.

The default metadata-only planner was run for the three frozen untouched sessions. No definition, statistics/open-interest, CBBO, or TCBBO market-data records were downloaded by this pricing run.

Frozen dates remain, in acquisition order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

The initial pricing-only planner displayed dates chronologically because the earlier multi-date parser sorted input. That display ordering did not expose endpoint data and did not alter the frozen validation-date set. The parser has since been changed to preserve first-seen caller order while de-duplicating dates, with a regression test covering the frozen batch-4 order.

## Metadata-only pricing result

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate | Chain status |
|---|---:|---:|---:|---|
| 2026-08-03 | $0.032331 | $0.012128 | $0.044459 | missing |
| 2026-07-31 | $0.032616 | $0.012515 | $0.045131 | missing |
| 2026-07-30 | $0.032830 | $0.012203 | $0.045033 | missing |

**Estimated definition + OI total for all three dates: $0.134623.**

Exact-symbol CBBO-1m cost is still pending because the three daily chain CSVs do not yet exist. Opening-only +/-200 TCBBO pricing is also pending until both chain and replay inputs exist so the opening forward can be determined under the frozen selection rule.

## Safety change before paid chain build

`scripts/gexy_multiday_plan.py` was hardened after the pricing run. `--build-missing-chains` now defaults to a zero-dollar fail-closed guard unless `--max-metadata-download-cost` is explicitly supplied. Before downloading any missing-chain definition/OI data, the script re-prices every missing date in the invocation and aborts before download if the re-priced total exceeds the reviewed guard.

The guard is a local preflight estimate guard, not a vendor transactional billing cap. Full-day CBBO remains a separate later acquisition stage with its own preflight cost guard.

## Reviewed paid metadata cap

After the $0 metadata-only estimate was confirmed and the fail-closed guard was verified through `--help`, the reviewed batch-4 missing-chain metadata cap is **$0.15 total** for the frozen three-date invocation.

The current estimate is $0.134623, leaving $0.015377 of preflight-estimate headroom. The paid chain build is authorized only if the immediate re-priced total is at or below $0.15. If the re-priced total exceeds $0.15, the script must abort before any definition/OI download and no higher cap should be substituted without a new recorded review.

This authorization covers only definition/statistics inputs needed to create the three daily 0DTE chain CSVs. It does **not** authorize full-day CBBO-1m, opening TCBBO, or any other market-data purchase.
