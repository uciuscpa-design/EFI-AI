# GEXY opening-window validation batch 4 protocol

## Status and purpose

This protocol is frozen after exhausting all eight previously cached replay/chain sessions and before generating, pricing, downloading, or inspecting any new batch-4 market data.

The prior eight opening-window sessions (2026-08-04 through 2026-08-13, excluding the weekend) are fully inspected research/validation data and must not be reused as fresh evidence. Post-hoc control-stability analysis found the ordinary opening 15-minute `hedge_delta_units` association negative on 8/8 existing sessions, while the historical momentum+raw two-control residual was negative on 7/8 and flipped only on 2026-08-06. That observation motivates a new candidate endpoint but does not rewrite the historical batch-3 verdict.

Batch 4 is a fresh untouched validation batch with two separately interpreted pre-specified endpoints: one for continuity with the historical validation architecture and one for prospective validation of the newly identified ordinary-association candidate.

## Frozen untouched dates and order

Use exactly these next three prior trading sessions, in this order:

1. **2026-08-03**
2. **2026-07-31**
3. **2026-07-30**

Do not substitute another date based on price, data quality, expected signal behavior, or intermediate endpoint results. A date may be skipped only for a documented technical unavailability or pre-reviewed budget reason; any skip must remain visible in the record and must not be replaced after inspecting signal results.

No batch-4 endpoint may be inspected until all authorized batch-4 acquisitions are complete.

## Frozen data scope

For every acquired date use exactly:

- SPXW 0DTE
- OPRA TCBBO for trade-flow inference
- opening flow window only: **09:30-10:00 America/New_York**
- strike scope: opening-forward +/- 200 SPX points
- the same exact-symbol selection logic used in batch 3
- the same frozen pre-trade NBBO aggressor classifier
- the same M+1 completed-minute causal availability rule
- the same Black-76 forward/IV/delta/gamma calculations
- the same hedge sign convention
- minimum classified-volume Greek coverage: **90%**
- horizon: **15 minutes only**

Do not purchase or analyze the closing window for batch 4. Do not add 5-minute, 1-minute, 30-minute, or 60-minute endpoints, call/put subcomponents, alternate coverage floors, alternate strike bands, or alternate aggressor rules to rescue or strengthen results.

## Endpoint A — historical continuity endpoint

Preserve the historical primary architecture exactly:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls:
  1. `backward_return_1m_bps`
  2. `flow_net_signed_contracts`
- statistic: rank-partial Spearman
- expected sign from the prior research set: **negative**

This endpoint is reported first for continuity with batch 3. Its outcome cannot be rescued by Endpoint B.

## Endpoint B — new ordinary-association candidate

Prospectively test the post-hoc 8/8 candidate without controls:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- statistic: ordinary Spearman
- expected sign from the inspected eight-session research set: **negative**

This is a newly pre-specified candidate endpoint for batch 4. It does not retroactively replace the batch-3 primary endpoint or convert the historical 8/8 pattern into out-of-sample evidence.

## Required reporting

For every acquired date report, on the same 90%-coverage opening-window sample:

1. observations
2. Endpoint A two-control partial Spearman
3. Endpoint B ordinary Spearman
4. momentum-only hedge partial Spearman, as a diagnostic only
5. raw-only hedge partial Spearman, as a diagnostic only
6. `hedge_delta_units` vs `flow_net_signed_contracts` Spearman
7. `hedge_delta_units` vs `backward_return_1m_bps` Spearman
8. `flow_net_signed_contracts` vs `backward_return_1m_bps` Spearman
9. Greek symbol-minute solve rate
10. classified-volume Greek coverage
11. replay-match count

After all acquired dates are processed, report separate day-level sign stability for Endpoint A and Endpoint B. Diagnostics cannot replace either endpoint.

## Pre-specified interpretation

Interpret the two endpoints separately:

- **Both mostly/all negative:** strengthens both the historical residual relationship and the new ordinary-association candidate, while still not proving causality or a production edge.
- **Endpoint B mostly/all negative but Endpoint A mixed:** supports the hypothesis that joint residualization is less stable than the underlying ordinary opening 15-minute hedge association.
- **Endpoint A mostly/all negative but Endpoint B mixed:** weakens the post-hoc ordinary 8/8 candidate while preserving evidence for the historical residual formulation.
- **Both mixed or collapse toward zero:** materially weakens the broader opening 15-minute relationship.

No success criterion permits changing signs, controls, horizons, classifier, strike band, coverage floor, or window after results are visible.

## Data-preparation and cost discipline

The current local cache contains no untouched replay+chain session beyond the eight already inspected dates. Therefore batch-4 replay/chain inputs must be prepared for the frozen dates before TCBBO can be bounded by the opening-forward +/-200 rule.

Before any market-data purchase for replay/chain preparation:

1. inspect the existing guarded replay planner/downloader and determine whether the required upstream data can be metadata-priced without downloading;
2. record metadata-only cost estimates and exact scope for all three frozen dates;
3. review the total budget before any paid command;
4. use hard per-invocation spend caps and immediate pre-download re-pricing where supported;
5. acquire all authorized upstream inputs before inspecting any trade-flow endpoint;
6. only after replay/chain caches exist, metadata-price opening-only +/-200 TCBBO for all three dates and review that second-stage budget before purchase.

No paid command is authorized by this protocol alone. Metadata-only pricing is not endpoint exposure.

## Epistemic limits

OPRA does not identify customer/dealer inventory or executed underlying dealer hedge trades. `hedge_delta_units` remains an opposite-side liquidity-provider hedge proxy derived from quote-based aggressor inference and Black-76 Greeks. Correlation or partial correlation does not establish causality or a deployable trading edge.
