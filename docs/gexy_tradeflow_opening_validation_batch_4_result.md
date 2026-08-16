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

## Post-validation heterogeneity audit — completed

A separate local-only audit was frozen after the Batch-4 result and before any additional Batch-4 heterogeneity diagnostic was run. Its detailed record is `docs/gexy_tradeflow_batch4_heterogeneity_audit_result.md`.

The audit sharpens the Batch-4 interpretation without changing the official endpoint results:

- **2026-07-31 ordinary positive is broad within the 29-observation sample.** All 29 leave-one-minute-out ordinary estimates remain positive, ranging from +0.195950 to +0.360153. The largest absolute ordinary rank-product contribution accounts for 10.41% of total absolute contribution and the top three account for 29.00%. The sign reversal is therefore not a one-minute artifact under the frozen diagnostics.
- **2026-08-03 ordinary negative is robust, but its positive two-control residual is sign-fragile.** All 29 ordinary leave-one-out estimates remain negative, while one of 29 controlled leave-one-out estimates becomes negative. The two controls explain 48.19% of ranked hedge variation on this day, supporting a control-sensitive residualization description without proving classical multicollinearity or a market mechanism.
- **2026-07-30 ordinary negative is robust, while the two-control residual is near zero and fragile.** All 29 ordinary leave-one-out estimates remain negative, but only 21 of 29 controlled estimates remain negative.

The audit therefore strengthens the conclusion that session heterogeneity is real and that the historical two-control residual is less sign-stable in Batch 4 than the ordinary association. It does not validate the ordinary endpoint, because 2026-07-31 remains a broad positive untouched failure.

## Research consequence

Do not change the sign convention, aggressor classifier, strike band, 90% coverage floor, or 15-minute horizon in response to Batch 4.

Do not discard or relabel 2026-07-31. It is a substantive untouched failure of the ordinary negative-sign candidate, and the heterogeneity audit indicates that its positive sign is broad within the small opening sample rather than driven by a single minute.

Do not let Endpoint B rescue the failed historical Endpoint A, and do not replace Endpoint A retroactively.

Do not mine the Batch-4 dates for a new regime classifier. Any next untouched validation batch must be frozen separately before acquisition and must explicitly acknowledge both facts now established descriptively: ordinary negative association can be stable on some sessions, and it can reverse broadly positive on another high-quality session.

No further TCBBO purchase should occur until that next untouched protocol and its budget discipline are frozen.