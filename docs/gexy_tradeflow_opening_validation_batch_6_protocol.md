# GEXY opening-window validation Batch 6 protocol

## Status and purpose

This protocol is frozen after Batch 5 and its separately frozen post-validation heterogeneity audit are complete, and before any Batch-6 market-data pricing, acquisition, extraction, or endpoint inspection.

The accumulated evidence no longer supports treating the opening 15-minute hedge/return relationship as a universal negative-sign hypothesis. Under the unchanged construction, prior untouched batches have produced negative, positive, and effectively near-zero day-level ordinary associations, with post-validation influence audits confirming that both broad positive and broad negative sessions can occur.

Batch 6 is therefore a **heterogeneity replication batch**, not a rescue attempt and not a search for a regime classifier. Its purpose is to collect another untouched consecutive block under the exact same construction and report the day-level sign and magnitude distribution without assuming that either sign should dominate.

## Frozen untouched dates and order

Use exactly these next three prior trading sessions, in this order:

1. **2026-07-24**
2. **2026-07-23**
3. **2026-07-22**

Do not substitute another date based on price, data quality, expected signal behavior, or intermediate results. A date may be skipped only for documented technical unavailability or a pre-reviewed budget reason; any skip must remain visible in the research record. Do not replace a skipped date after seeing any endpoint result.

No Batch-6 endpoint may be inspected until all authorized Batch-6 acquisitions and local preparation are complete.

## Frozen data scope

For every acquired date use exactly:

- SPXW 0DTE
- OPRA TCBBO
- opening flow window only: **09:30-10:00 America/New_York**
- strike scope: opening-forward +/-200 SPX points
- same exact-symbol selection logic used in prior batches
- same frozen pre-trade NBBO aggressor classifier
- same M+1 completed-minute causal availability rule
- same Black-76 forward/IV/delta/gamma calculations
- same hedge sign convention
- minimum classified-volume Greek coverage: **90%**
- horizon: **15 minutes only**

Do not purchase or analyze the closing window. Do not add 1m, 5m, 30m, 60m, call/put decomposition, alternate coverage floors, alternate strike bands, alternate aggressor rules, or a market-regime split.

## Endpoint A — historical continuity

Preserve the historical two-control endpoint unchanged and report it first for continuity:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls:
  1. `backward_return_1m_bps`
  2. `flow_net_signed_contracts`
- statistic: rank-partial Spearman

Batch 4 and Batch 5 already weakened this architecture. Batch 6 is an additional untouched stability observation, not a reset or re-validation of the earlier negative hypothesis.

## Endpoint B — ordinary heterogeneity endpoint

Keep the ordinary endpoint unchanged:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: none
- statistic: ordinary Spearman

Endpoint B is now interpreted descriptively as a day-level heterogeneity endpoint. Report each untouched day's signed value, the number of negative and positive days, the median, minimum, and maximum.

Do **not** pre-label a day as a new market regime from the sign alone. Do not define a post-hoc threshold for 'near zero' after seeing Batch-6 values. If an influence/stability audit is later warranted, it must be frozen separately after the official Batch-6 result is permanently recorded.

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

No leave-one-out, contribution concentration, subwindow, alternate horizon, or new market-state diagnostic is part of the primary Batch-6 reveal.

## Pre-specified interpretation

Batch 6 is evaluated as a heterogeneity replication, not by whether a negative sign 'wins.'

For Endpoint B:

- **Mixed signs across the three days:** directly replicates cross-session sign heterogeneity under the unchanged construction.
- **All three same sign:** shows a locally coherent three-session block, but does not restore universality because prior untouched broad opposite-sign sessions remain part of the cumulative record.
- **One or more values close to zero in magnitude:** report the exact magnitude without inventing a threshold-based state label. Any influence characterization must wait for a separately frozen post-result audit.

For Endpoint A:

- mixed signs or mostly positive values further reinforce instability of the historical two-control architecture;
- consistently negative values are new stability evidence only and cannot undo the prior Batch-4/5 failures.

No outcome permits changing the signal definition, controls, sign convention, classifier, horizon, window, strike band, or coverage floor after results are visible.

## Cumulative research framing

Batch 6 must preserve all prior failures and opposite-sign sessions in the cumulative record. In particular, it must not erase the broad positive sessions documented on 2026-07-31 and 2026-07-28 or the broad negative sessions documented on 2026-08-03, 2026-07-30, and 2026-07-27.

The research question is now whether the unchanged construction continues to exhibit day-level heterogeneity—not whether a universal negative sign can be recovered.

## Cost and acquisition discipline

Batch 6 starts with **no authorization for paid market-data requests**.

Use the same staged fail-closed process as prior batches:

1. metadata-price Definition/statistics chain inputs for the three frozen dates without downloading;
2. review and record exact chain-input cost estimates;
3. set an explicit reviewed metadata cap before any chain acquisition;
4. after chains exist, metadata-price exact-symbol full-day CBBO-1m replay inputs;
5. review and record a separate CBBO cap before download;
6. build all three replay caches before pricing TCBBO;
7. metadata-price only the frozen opening 09:30-10:00 +/-200 TCBBO scope for all three dates;
8. review per-date TCBBO caps before any paid TCBBO command;
9. acquire all three authorized TCBBO files in frozen date order before endpoint extraction or inspection;
10. run local preparation for all three dates before one dedicated Batch-6 15m reveal.

No higher cap may be substituted after an over-cap preflight without a new recorded review.

## Epistemic limits

`hedge_delta_units` remains an opposite-side liquidity-provider hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify customer/dealer inventory or executed underlying hedge trades.

Correlation, partial correlation, sign stability, heterogeneity, and any later influence diagnostic do not establish causality or a deployable trading edge.
