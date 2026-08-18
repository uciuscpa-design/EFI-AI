# GEXY opening-window validation Batch 5 acquisition closure

## Status

Batch 5 paid acquisition is complete before any endpoint extraction or inspection.

Frozen dates and acquisition order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

Frozen TCBBO scope remained unchanged: SPXW 0DTE, OPRA TCBBO, 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, 15-minute horizon downstream, and the previously frozen classifier/sign/Greek construction.

## Completed opening TCBBO acquisition

| Date | Selected contracts | Immediate pre-download re-price | Reviewed cap | Result |
|---|---:|---:|---:|---|
| 2026-07-29 | 160 | $1.651881 | $1.70 | downloaded and cached |
| 2026-07-28 | 160 | $2.003905 | $2.07 | downloaded and cached |
| 2026-07-27 | 160 | $2.247783 | $2.32 | downloaded and cached |

All three immediate re-prices matched the prior metadata-only estimates and remained below their reviewed caps.

The three raw files are:

- `data/gexy/tradeflow/gexy_spxw_2026-07-29_0930_1000_tcbbo.dbn.zst`
- `data/gexy/tradeflow/gexy_spxw_2026-07-28_0930_1000_tcbbo.dbn.zst`
- `data/gexy/tradeflow/gexy_spxw_2026-07-27_0930_1000_tcbbo.dbn.zst`

The summed pre-download TCBBO estimate used for the three successful requests was **$5.903569**. Combined with the earlier Batch-5 Definition/OI estimate of $0.134707 and full-day exact-symbol CBBO estimate of $0.080599, cumulative estimate-based Batch-5 acquisition accounting is **$6.118875**. These are pre-download estimates/guards, not final vendor invoice amounts.

## Duplicate July 28 invocation

After the successful 2026-07-28 acquisition, the same paid command was accidentally invoked a second time. The downloader detected the existing final file and exited with:

`refusing to overwrite existing trade-flow files: data\gexy\tradeflow\gexy_spxw_2026-07-28_0930_1000_tcbbo.dbn.zst`

The duplicate invocation did not perform another TCBBO download. It does not change the frozen acquisition order or the successful original July 28 acquisition.

## Acquisition phase closed

No more paid Batch-5 market-data acquisition is required for the frozen validation reveal. From this checkpoint through local feature construction and endpoint evaluation, the planned workflow is local-only and $0.

No Batch-5 endpoint has been extracted or inspected yet. A Batch-5-specific local preparation wrapper and dedicated 15-minute validator must be frozen before the first endpoint computation. The official Batch-5 reveal must occur only after all three dates complete local preparation.