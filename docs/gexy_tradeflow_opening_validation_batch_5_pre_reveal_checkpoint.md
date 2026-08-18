# GEXY opening-window validation Batch 5 pre-reveal checkpoint

## Status

This checkpoint is recorded after all authorized Batch-5 acquisition is complete and before any Batch-5 validation endpoint is computed or inspected.

Frozen dates remain, in order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

The original Batch-5 protocol remains controlling: opening 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, SPXW 0DTE TCBBO, frozen pre-trade NBBO aggressor classifier, M+1 causal availability, Black-76 Greeks, unchanged hedge sign convention, 90% classified-volume Greek coverage floor, and 15-minute horizon only.

## Acquisition closure

All three frozen TCBBO files have been acquired after immediate re-pricing within reviewed per-date caps. The summed TCBBO pre-download estimate was $5.903569. Earlier Batch-5 Definition/OI and full-day exact-symbol CBBO pre-download estimates were $0.134707 and $0.080599 respectively, for cumulative estimate-based acquisition accounting of $6.118875. These are estimate/guard values rather than final vendor invoice amounts.

A duplicate second invocation for 2026-07-28 was safely rejected because the final raw TCBBO file already existed; no duplicate TCBBO download occurred.

No further paid market-data request is required before the Batch-5 validation reveal.

## Frozen local preparation implementation

Batch-5-specific wrapper:

- `scripts/gexy_tradeflow_prepare_batch5.py`
- implementation commit: `448b0a2dbd2f90835b1d779fb2d107ae720ae563`
- CLI/order safeguard test: `tests/test_gexy_tradeflow_prepare_batch5_cli.py`
- test commit: `7912dffe48d7a82616c40c084de80173649b6e53`

The wrapper is fixed to:

- window 09:30-10:00
- strike band +/-200 points
- horizon labels 15 minutes only
- existing local chain/replay/TBCBO caches only
- sequential extract -> raw causal features -> Greek hedge features
- per-date preparation logs named with `batch5`
- no validation endpoint evaluation
- no market-data request

## Frozen Batch-5 validator implementation

Dedicated validator:

- `scripts/gexy_tradeflow_opening_validation_batch5.py`
- implementation commit: `3bb481f0f99d897e8a3ff544d0d1eaf28c6d9957`
- CLI/order safeguard test: `tests/test_gexy_tradeflow_opening_validation_batch5_cli.py`
- test commit: `512e010cede240226c370a533a1f724e4798e954`

The validator is fixed to the 15-minute opening sample and 90% coverage floor. It reports, without tuning:

- Endpoint A: rank-partial Spearman of `hedge_delta_units` vs `forward_return_15m_bps`, controlling `backward_return_1m_bps` and `flow_net_signed_contracts`
- Endpoint B: ordinary Spearman of `hedge_delta_units` vs `forward_return_15m_bps`
- momentum-only partial
- raw-only partial
- hedge/raw, hedge/momentum, raw/momentum Spearman
- observations
- opening replay-match count
- median Greek solve rate
- median classified-volume Greek coverage
- separate day-level sign counts and medians for A and B

Outputs are Batch-5-specific and do not overwrite Batch-4 CSVs.

## Local preparation completion

The two Batch-5 safeguard test files were run together before local preparation and completed successfully with **4 passed**.

The Batch-5 preparation wrapper was then run once across the complete frozen date set in the frozen order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

For every date, all three local stages completed successfully:

- `extract: OK`
- `raw_features: OK`
- `hedge_features: OK`

The wrapper concluded with:

- `BATCH-5 LOCAL PREPARATION COMPLETE`
- `DATES PREPARED: 3`
- `NO PAID DATA REQUESTS: all stages read only existing local caches.`
- `NO VALIDATION ENDPOINTS EVALUATED: run the frozen Batch-5 validator separately after preparation.`

Therefore the complete frozen three-date feature set is prepared and the Batch-5 endpoints remain unseen at this checkpoint.

## Reveal discipline

The next permitted operation is one local-only invocation of the dedicated Batch-5 validator across all three dates simultaneously. No date-by-date endpoint inspection or alternate analysis should occur first.

The Batch-5 validator is local-only and makes no paid data request. The eventual result cannot erase Batch-4 failures, cannot retroactively validate the earlier 8/8 pattern, and cannot establish causality, dealer inventory, or production edge.