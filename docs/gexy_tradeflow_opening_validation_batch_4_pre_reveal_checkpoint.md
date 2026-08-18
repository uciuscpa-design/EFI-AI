# GEXY opening-window validation Batch 4 — pre-reveal checkpoint

## Status

This checkpoint is recorded after all frozen Batch-4 market-data acquisitions and all local feature-preparation stages completed, but before the Batch-4 validation endpoints are evaluated or inspected.

Frozen dates and order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

Frozen validation scope remains unchanged:

- SPXW 0DTE
- opening window 09:30-10:00 America/New_York only
- opening-forward +/-200 SPX points
- pre-trade NBBO aggressor classifier
- M+1 completed-minute availability
- Black-76 Greek weighting
- 90% minimum classified-volume Greek coverage
- 15-minute horizon only
- Endpoint A: `hedge_delta_units` partial Spearman controlling `backward_return_1m_bps` and `flow_net_signed_contracts`, expected negative
- Endpoint B: ordinary Spearman between `hedge_delta_units` and `forward_return_15m_bps`, expected negative

## Acquisition completion

All three opening TCBBO files were acquired in the frozen order after immediate pre-download cost checks. The pre-download estimates matched the previously reviewed estimates:

| Date | TCBBO pre-download estimate | Reviewed cap |
|---|---:|---:|
| 2026-08-03 | $2.381683 | $2.45 |
| 2026-07-31 | $2.521779 | $2.60 |
| 2026-07-30 | $2.105496 | $2.18 |

Total TCBBO pre-download estimate used: **$7.008959**.

Combined with the previously completed definition/OI and CBBO replay stages, the cumulative Batch-4 upstream preflight estimate remains **$7.245478**. This is an estimate-based research budget record, not a statement of final vendor billing.

No validation endpoint was inspected between acquisitions.

## Local preparation completion

The dedicated Batch-4 preparation CLI and validator safeguards were pulled and tested before feature preparation. The local test command reported **4 passed**.

The Batch-4 local preparation wrapper was then run once for all three frozen dates in the frozen order. For each date, all three stages completed successfully:

- TCBBO extraction/classification
- causal raw minute-flow feature construction
- Greek-weighted hedge-flow feature construction

The wrapper reported:

- `DATES PREPARED: 3`
- `NO PAID DATA REQUESTS`
- `NO VALIDATION ENDPOINTS EVALUATED`

Per-day preparation logs were written under `data/gexy/tradeflow/`.

## Reveal rule

The next permitted action is a single local-only run of `scripts/gexy_tradeflow_opening_validation_batch4.py` over all three frozen dates together with the frozen 90% coverage floor. That validator evaluates **15 minutes only** and reports Endpoint A and Endpoint B separately, along with the pre-specified control/quality diagnostics.

Do not run the older Batch-3 validator, alternate horizons, alternate coverage floors, call/put decompositions, alternate windows, or post-hoc rescue analyses before recording the Batch-4 result.

No Batch-4 validation endpoint has been evaluated or inspected at the time of this checkpoint.
