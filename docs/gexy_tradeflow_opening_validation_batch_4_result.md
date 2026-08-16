# GEXY opening-window validation batch 4 result

## Status

This document records the fresh untouched Batch-4 validation result after the protocol, dates, acquisition order, data scope, 15-minute horizon, 90% classified-volume Greek coverage floor, Endpoint A, and Endpoint B were frozen before Batch-4 TCBBO acquisition or endpoint inspection.

Validation dates, in frozen order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

Frozen scope:

- SPXW 0DTE TCBBO
- 09:30-10:00 America/New_York only
- opening-forward +/-200 SPX points
- frozen pre-trade NBBO aggressor classifier
- M+1 causal availability
- Black-76 Greek weighting
- 90% classified-volume Greek coverage floor
- unchanged hedge sign convention
- horizon: 15 minutes only

All three authorized TCBBO acquisitions were completed before any Batch-4 endpoint was inspected. Local preparation then completed for all three dates before the dedicated Batch-4 validator was run once across the full frozen date set.

## Endpoint A — historical continuity endpoint

Endpoint A preserves the historical Batch-3 architecture:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: `backward_return_1m_bps` and `flow_net_signed_contracts`
- statistic: rank-partial Spearman
- expected sign: negative

| Trading day | Observations | Endpoint A partial Spearman | Negative sign |
|---|---:|---:|---|
| 2026-08-03 | 29 | +0.107961 | no |
| 2026-07-31 | 29 | +0.372243 | no |
| 2026-07-30 | 29 | -0.023649 | yes |

Endpoint A sign stability:

- days: 3
- negative days: **1 / 3 (33.3%)**
- median partial Spearman: **+0.107961**
- range: **-0.023649 to +0.372243**

**Result:** Endpoint A does not validate on Batch 4. The historical two-control residual is positive on two of the three untouched sessions and its median is positive.

## Endpoint B — prospectively frozen ordinary-association candidate

Endpoint B prospectively tests the post-hoc ordinary opening-15m candidate identified on the previously inspected eight-session set:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: none
- statistic: ordinary Spearman
- expected sign: negative

| Trading day | Observations | Endpoint B ordinary Spearman | Negative sign |
|---|---:|---:|---|
| 2026-08-03 | 29 | -0.136453 | yes |
| 2026-07-31 | 29 | +0.272906 | no |
| 2026-07-30 | 29 | -0.145813 | yes |

Endpoint B sign stability:

- days: 3
- negative days: **2 / 3 (66.7%)**
- median ordinary Spearman: **-0.136453**
- range: **-0.145813 to +0.272906**

**Result:** Endpoint B partially replicates directionally but does not cleanly validate. Two untouched sessions retain the expected negative sign, while 2026-07-31 shows a substantive positive reversal.

Endpoint B must not be used to rescue Endpoint A, and it does not retroactively convert the prior inspected 8/8 ordinary pattern into out-of-sample evidence.

## Frozen diagnostics

| Trading day | Hedge partial \| momentum | Hedge partial \| raw | Hedge vs raw | Hedge vs momentum | Raw vs momentum |
|---|---:|---:|---:|---:|---:|
| 2026-08-03 | +0.031679 | -0.127053 | +0.273399 | +0.561576 | -0.221675 |
| 2026-07-31 | +0.346026 | +0.299584 | +0.149754 | +0.219704 | +0.038424 |
| 2026-07-30 | -0.030407 | -0.186960 | -0.128079 | +0.733990 | -0.198030 |

These diagnostics are not alternate endpoints and do not change the frozen adjudication.

Two distinct failure patterns are visible descriptively:

- **2026-08-03:** the ordinary association is negative (-0.136453), raw-only residual remains negative (-0.127053), but momentum-only is slightly positive (+0.031679) and the joint two-control Endpoint A is positive (+0.107961). This is consistent with control-sensitive residualization on this session, but does not prove a suppression mechanism.
- **2026-07-31:** the ordinary association itself is positive (+0.272906), and both single-control residuals and the joint Endpoint A are also positive. This is a genuine sign reversal of the observed opening association, not merely a joint-control sign flip.
- **2026-07-30:** the ordinary association and all frozen residual variants remain negative, although Endpoint A is near zero (-0.023649).

## Data-quality audit from the frozen validator

| Trading day | Replay matches / opening rows | Median symbol-minute Greek solve rate | Median classified volume with Greeks |
|---|---:|---:|---:|
| 2026-08-03 | 30 / 30 | 96.86% | 99.87% |
| 2026-07-31 | 30 / 30 | 96.08% | 99.87% |
| 2026-07-30 | 30 / 30 | 96.72% | 99.85% |

All three sessions have complete 30/30 opening replay matching, high median symbol-minute Greek solve rates, and approximately 99.85%-99.87% median classified-volume Greek coverage. The positive Endpoint-A outcomes and the 2026-07-31 Endpoint-B reversal therefore should not be attributed to an obvious replay or Greek-coverage failure.

## Interpretation against the frozen protocol

The frozen protocol stated that if both endpoints are mixed or collapse toward zero, the broader opening 15-minute relationship is materially weakened.

Batch 4 therefore **materially weakens the broader opening 15-minute hypothesis**:

- the historical two-control continuity endpoint fails to generalize in this batch;
- the ordinary candidate is more sign-stable than Endpoint A in this batch, but only 2/3 negative and therefore not a clean prospective validation;
- 2026-07-31 is especially important because it reverses the ordinary association itself, showing that the previously observed negative opening tendency is not universal;
- 2026-08-03 separately shows that residualization can again move a negative ordinary association to a positive joint-control residual.

The scientifically defensible conclusion is not that the signal is dead, nor that the ordinary endpoint is established. The evidence now supports a **conditional, heterogeneous opening relationship** whose sign and incremental content vary across sessions. Any production claim, universal dealer-hedging mechanism claim, or stable edge claim would be unsupported.

OPRA does not identify customer/dealer inventory or executed underlying dealer hedge trades. `hedge_delta_units` remains an opposite-side liquidity-provider hedge proxy derived from quote-based aggressor inference and Black-76 Greeks. Correlation and partial correlation do not establish causality.

## Research consequence

Do not change the sign convention, aggressor classifier, strike band, 90% coverage floor, or 15-minute horizon in response to Batch 4.

Do not discard or relabel 2026-07-31. It is a substantive untouched failure of the ordinary negative-sign candidate.

Do not let Endpoint B rescue the failed historical Endpoint A.

Before purchasing more TCBBO, perform a **local-only Batch-4 heterogeneity audit** that is explicitly diagnostic rather than signal-selective. The next audit should compare the three Batch-4 sessions on already-frozen observables and control structure, with particular attention to why 2026-07-31 reverses the ordinary association and why 2026-08-03 changes sign only after residualization. No new horizon, window, strike band, classifier, coverage threshold, or signal decomposition should be introduced in that audit.

Any later untouched validation batch must be frozen separately before acquisition and must preserve the Batch-4 failures in the cumulative research record.