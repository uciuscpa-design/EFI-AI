# GEXY opening-window validation batch 5 protocol

## Status and purpose

This protocol is frozen after Batch 4 and its frozen heterogeneity audit are complete, and before any Batch-5 market-data pricing, acquisition, extraction, or endpoint inspection.

Batch 4 materially weakened the hypothesis of a universal negative opening 15-minute hedge/return relationship. Its post-validation heterogeneity audit showed two distinct facts that must both remain visible:

- ordinary `hedge_delta_units` vs 15-minute forward return can be stably negative within a session (2026-08-03 and 2026-07-30 remained negative under every leave-one-minute-out deletion), and
- the ordinary association can also reverse broadly positive on a high-quality untouched session (2026-07-31 remained positive under every leave-one-minute-out deletion).

Batch 5 therefore does **not** search for a regime classifier. Its purpose is to collect another small untouched block under the exact same opening-window construction and measure whether the sign heterogeneity seen in Batch 4 recurs.

## Frozen untouched dates and order

Use exactly these next three prior trading sessions, in this order:

1. **2026-07-29**
2. **2026-07-28**
3. **2026-07-27**

Do not substitute another date based on cost, data quality, expected signal behavior, or intermediate results. A date may be skipped only for documented technical unavailability or a pre-reviewed budget reason, and any skip must remain visible in the record. Do not replace a skipped date after seeing any endpoint result.

No Batch-5 endpoint may be inspected until all authorized Batch-5 acquisitions and local preparation are complete.

## Frozen data scope

For every acquired date use exactly:

- SPXW 0DTE
- OPRA TCBBO
- opening flow window only: **09:30-10:00 America/New_York**
- strike scope: opening-forward +/- 200 SPX points
- the same exact-symbol selection logic used in Batches 3 and 4
- the same frozen pre-trade NBBO aggressor classifier
- the same M+1 completed-minute causal availability rule
- the same Black-76 forward/IV/delta/gamma calculations
- the same hedge sign convention
- minimum classified-volume Greek coverage: **90%**
- horizon: **15 minutes only**

Do not purchase or analyze the closing window. Do not add 1m, 5m, 30m, 60m, call/put decomposition, alternate coverage floors, alternate strike bands, alternate aggressor rules, or a market-regime split.

## Endpoint A — historical continuity

Keep the historical continuity endpoint unchanged:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls:
  1. `backward_return_1m_bps`
  2. `flow_net_signed_contracts`
- statistic: rank-partial Spearman

Report it first for continuity with prior batches. The prior negative directional hypothesis has already failed clean validation in Batch 4; Batch 5 is therefore a further untouched stability check, not a reset of that failed validation.

## Endpoint B — ordinary association stability

Keep the ordinary endpoint unchanged:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: none
- statistic: ordinary Spearman

The earlier research set showed a post-hoc 8/8 negative pattern, while Batch 4 prospectively produced 2/3 negative and one broad positive reversal. Batch 5 therefore tests sign stability without assuming the relationship is universal.

The pre-specified reporting question is:

- how many of the three untouched Batch-5 days are negative versus positive, and how large are the day-level associations?

Do not call Endpoint B validated merely because it is negative on a majority of three days. Conversely, any positive day remains substantive heterogeneity and must not be discarded.

## Required diagnostics

For every date, on the same frozen 90%-coverage opening sample, report:

1. observations
2. Endpoint A two-control partial Spearman
3. Endpoint B ordinary Spearman
4. momentum-only hedge partial Spearman
5. raw-only hedge partial Spearman
6. hedge/raw Spearman
7. hedge/momentum Spearman
8. raw/momentum Spearman
9. opening replay-match count
10. median symbol-minute Greek solve rate
11. median classified-volume Greek coverage

After all three dates are processed, report separate sign counts and medians for Endpoint A and Endpoint B.

No leave-one-out or contribution diagnostic is part of the primary Batch-5 reveal. Those may be considered only after the untouched Batch-5 result is permanently recorded, under a separately frozen diagnostic protocol if needed.

## Pre-specified interpretation

Batch 5 is a stability/heterogeneity replication batch, not a rescue attempt.

- **Endpoint B negative on all 3 days:** strengthens evidence that the negative ordinary association is common under this construction, but does not erase the broad positive 2026-07-31 failure or establish universality/production edge.
- **Endpoint B negative on 2/3 days:** repeats the Batch-4 qualitative pattern and supports a conditional/heterogeneous relationship.
- **Endpoint B negative on 0-1/3 days:** materially weakens the idea that the negative ordinary association is even the dominant sign in nearby sessions.
- **Endpoint A remains mixed or mostly positive:** further weakens the historical two-control architecture.
- **Endpoint A becomes consistently negative:** counts as new stability evidence only; it does not retroactively undo the Batch-4 failure.

No outcome permits changing the signal definition, controls, sign convention, classifier, horizon, window, strike band, or coverage floor after results are visible.

## Cost and acquisition discipline

Batch 5 starts with no authorization for paid market-data requests.

Use the same staged process as Batch 4:

1. metadata-price definition/statistics inputs for the three frozen dates without downloading;
2. review and record exact chain-input cost estimates;
3. use a fail-closed explicit cap and immediate pre-download re-pricing for any chain acquisition;
4. after chains exist, metadata-price exact-symbol full-day CBBO-1m replay inputs;
5. review and record a separate explicit CBBO cap before download;
6. build all three replay caches before pricing TCBBO;
7. metadata-price only the frozen opening 09:30-10:00 +/-200 TCBBO scope for all three dates;
8. review per-date TCBBO caps before any paid TCBBO command;
9. acquire all three authorized TCBBO files in frozen date order before any endpoint extraction or inspection;
10. run local preparation for all three dates before one dedicated Batch-5 15m reveal.

No higher cap may be substituted after an over-cap preflight without a new recorded review.

## Epistemic limits

`hedge_delta_units` remains an opposite-side liquidity-provider hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify customer/dealer inventory or executed underlying hedge trades.

Correlation, partial correlation, sign stability, and any later influence diagnostic do not establish causality or a deployable trading edge.
