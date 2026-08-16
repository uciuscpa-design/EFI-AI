# GEXY opening-window validation Batch 6 pre-reveal checkpoint

## Status

This checkpoint is recorded after all authorized Batch-6 acquisition is complete and before any Batch-6 validation endpoint is computed or inspected.

Frozen dates remain, in order:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

The Batch-6 protocol remains controlling: SPXW 0DTE, opening 09:30-10:00 America/New_York only, opening-forward +/-200 SPX points, frozen pre-trade NBBO aggressor classifier, M+1 causal availability, Black-76 Greeks, unchanged hedge sign convention, 90% classified-volume Greek coverage floor, and 15-minute horizon only.

Batch 6 is a heterogeneity replication. Endpoint B has no pre-assumed dominant sign.

## Acquisition closure

All three frozen TCBBO files were acquired after immediate re-pricing within reviewed per-date caps:

- 2026-07-24: estimate/recheck $2.076316, cap $2.14
- 2026-07-23: estimate/recheck $2.356086, cap $2.43
- 2026-07-22: estimate/recheck $1.901407, cap $1.96

Summed TCBBO pre-download estimate: **$6.333809**.

Earlier Batch-6 Definition/OI and full-day exact-symbol CBBO pre-download estimates were **$0.136567** and **$0.084454** respectively, for cumulative estimate-based acquisition accounting of **$6.554830**. These are estimate/guard values, not final vendor invoice amounts.

No further paid market-data request is required before the Batch-6 reveal.

## Frozen local preparation implementation

Batch-6-specific wrapper:

- `scripts/gexy_tradeflow_prepare_batch6.py`
- implementation commit: `5d6916c974fd426b1ecbbd17cabe32a12eab95e7`
- CLI/order safeguard: `tests/test_gexy_tradeflow_prepare_batch6_cli.py`
- safeguard commit: `c23a5c0f6f14fa269cd06a233326089d477cf8a6`

The wrapper is fixed to:

- 09:30-10:00 only
- opening-forward +/-200 points
- 15-minute labels only
- already acquired local chain/replay/TCBBO caches
- sequential extract -> raw causal features -> Greek hedge features
- Batch-6-specific preparation logs
- no validation endpoint evaluation
- no market-data request

## Frozen Batch-6 validator implementation

Dedicated validator:

- `scripts/gexy_tradeflow_opening_validation_batch6.py`
- implementation commit: `e7584425d0e5e69fa1932c9c086f90bd94bb1aa1`
- CLI/order safeguard: `tests/test_gexy_tradeflow_opening_validation_batch6_cli.py`
- safeguard commit: `afb70ef1cc9cc1f02bd01c7585f48313ca53a321`

The validator is fixed to the opening 15-minute sample and 90% coverage floor. It reports without tuning:

- Endpoint A: rank-partial Spearman of `hedge_delta_units` vs `forward_return_15m_bps`, controlling `backward_return_1m_bps` and `flow_net_signed_contracts`
- Endpoint B: ordinary Spearman of `hedge_delta_units` vs `forward_return_15m_bps`, interpreted as a heterogeneity endpoint with no assumed dominant sign
- momentum-only partial
- raw-only partial
- hedge/raw, hedge/momentum, raw/momentum Spearman
- observations
- opening replay-match count
- median Greek solve rate
- median classified-volume Greek coverage
- separate negative, positive, and exact-zero day counts plus median/min/max for A and B

Outputs are Batch-6-specific and do not overwrite prior-batch CSVs.

## Reveal discipline

Run the safeguard tests first. Then run Batch-6 local preparation across all three frozen dates in one invocation. Do not run the validator if preparation fails on any date.

If preparation completes for all three dates, record that completion before running the dedicated validator once across all three dates. No endpoint should be inspected date-by-date before the full three-date reveal.

No leave-one-out, contribution-concentration, subwindow, alternate horizon, or regime diagnostic is part of the primary reveal. Any post-result diagnostic requires a separately frozen protocol after the official Batch-6 result is recorded.

## Scientific limits

The result cannot erase prior broad positive, broad negative, or near-zero sessions. It cannot establish a regime classifier, causality, observed dealer inventory, executed hedge flow, or a production trading edge.
