# GEXY temporal-extension holdout cost plan

## Status

This cost plan is governed by the separately frozen temporal-extension holdout protocol. The three reserved dates remain a temporal-extension holdout and are not being used to rescue the failed 09:40 session-state screen.

Reserved holdout dates, in frozen order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

No endpoint value may be inspected until all frozen holdout acquisition/preparation stages are complete and the dedicated holdout reveal is ready.

## Stage 1 — definition + OI chain inputs

Initial metadata-only estimates:

| Date | Definition estimate | Statistics/OI estimate | Total metadata estimate |
|---|---:|---:|---:|
| 2026-07-21 | $0.033219 | $0.012674 | $0.045893 |
| 2026-07-20 | $0.033226 | $0.012015 | $0.045241 |
| 2026-07-17 | $0.032428 | $0.012373 | $0.044801 |

Exact estimated definition+OI total: **$0.135936**.

Reviewed Stage-1 guard: **$0.15 total**.

Executed paid command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-07-21,2026-07-20,2026-07-17 --build-missing-chains --max-metadata-download-cost 0.15
```

Immediate preflight re-price remained **$0.135936**, below the $0.15 guard, so the definition/statistics requests proceeded.

Stage-1 outputs:

| Date | Chain contracts | Chain status |
|---|---:|---|
| 2026-07-21 | 490 | built |
| 2026-07-20 | 474 | built |
| 2026-07-17 | 1018 | built |

The planner explicitly reported that Stage 1 downloaded definition/statistics data only. Full-day CBBO quotes were **not** downloaded in this stage.

## Stage 2 — exact-symbol full-day CBBO

With all three cached chains available, the exact-symbol 09:30-16:00 America/New_York CBBO-1m estimates were:

| Date | Contracts | Exact-symbol CBBO-1m estimate |
|---|---:|---:|
| 2026-07-21 | 490 | $0.024306 |
| 2026-07-20 | 474 | $0.026450 |
| 2026-07-17 | 1018 | $0.054968 |

Exact Stage-2 CBBO total estimate: **$0.105724**.

Reviewed Stage-2 new-CBBO guard: **$0.12 total**.

Executed paid command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_replay.py --dates 2026-07-21,2026-07-20,2026-07-17 --download --max-new-cbbo-cost 0.12
```

Immediate Stage-2 pre-download re-price remained **$0.105724**, below the $0.12 guard. All three dates completed and the replay driver saved `gexy_spxw_multiday_replay_manifest.csv`.

Observed replay preparation included:

- 2026-07-20: 474 contracts, 118610 cached quote rows, 388 replay minutes, 1 minute skipped for low parity pairs, and replay features saved.
- 2026-07-17: 1018 contracts, 226038 cached quote rows, 389 replay minutes, 0 minutes skipped for low parity pairs, and replay features saved.
- 2026-07-21 also completed as part of the three-date multiday replay; the user-provided transcript excerpt did not include its detailed replay row counts, so none are invented here.

The multiday driver reported `DATES: 3`, `RE-PRICED NEW CBBO COST USED FOR GUARD: $0.105724`, and a saved manifest. Re-running after the quote CSVs exist should reuse cached CBBO at $0 new CBBO download cost.

Estimated cumulative Stage-1 + Stage-2 data cost based on the frozen estimates: **$0.241660**.

The replay-generated state/features remain preparation artifacts only. Do not inspect or adjudicate the temporal-extension Endpoint-B holdout result yet.

## Stage 3 — opening TCBBO tradeflow

Opening TCBBO acquisition remains **not yet authorized**.

The exact frozen Stage-3 scope is:

- dates: 2026-07-21, 2026-07-20, 2026-07-17;
- window: 09:30-10:00 America/New_York only;
- schema: OPRA TCBBO;
- strike scope: opening-forward ±200 SPX points;
- exact symbols selected from each cached same-day SPXW 0DTE chain;
- pricing first, with no `--execute` flag;
- separate reviewed per-date cap required before each paid request.

The fail-closed downloader `scripts/gexy_tradeflow_download.py` prices the exact request without downloading when `--execute` is omitted. It re-prices the exact request immediately before any paid download, rejects any estimate above the explicit cap, refuses to overwrite existing TCBBO files, and has a hard absolute $5 ceiling.

### Dry-run estimates

| Date | Opening forward | Exact symbols | Opening TCBBO estimate | Status |
|---|---:|---:|---:|---|
| 2026-07-21 | 7481.846627 | 160 | $1.988368 | dry run only; no download |
| 2026-07-20 | 7501.515003 | 160 | $2.240789 | dry run only; no download |
| 2026-07-17 | pending | pending | pending | not yet priced |

The 2026-07-21 and 2026-07-20 dry runs used exactly the frozen 09:30-10:00 window and ±200-point strike band. Each successful downloader run explicitly reported `DRY RUN ONLY: no market data downloaded`. An earlier duplicated 2026-07-20 command failed argument parsing at `--max-cost` and therefore did not price or download data.

The first 2026-07-17 dry-run attempt was also duplicated on one PowerShell line, so `--max-cost` was parsed as the invalid value `5uv`. Argument parsing failed before any pricing request or market-data download; 2026-07-17 remains pending.

Next steps:

1. price 2026-07-17 using the same frozen dry-run scope;
2. record all three exact per-date estimates;
3. freeze separate reviewed TCBBO caps before any paid TCBBO request;
4. acquire/extract/build tradeflow features without revealing the holdout Endpoint B;
5. run the dedicated frozen holdout reveal only after all preparation is complete.

## Scientific and cost limits

The three dates remain an untouched temporal-extension holdout with respect to the endpoint result. Acquisition order, construction, opening window, 15-minute horizon, 90% Greek-volume coverage floor, hedge sign convention, and Endpoint-B definition remain governed by the frozen holdout protocol.

Paid requests require explicit reviewed caps and user execution. Re-running already-cached local stages must not trigger new downloads.
