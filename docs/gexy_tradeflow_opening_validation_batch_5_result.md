# GEXY opening-window validation Batch 5 result

## Status

This document records the fresh untouched Batch-5 validation result after the protocol, frozen dates/order, acquisition scope, 15-minute horizon, 90% classified-volume Greek coverage floor, Endpoint A, and Endpoint B were fixed before Batch-5 endpoint inspection.

Frozen dates, in order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

Frozen scope remained unchanged:

- SPXW 0DTE TCBBO
- opening window 09:30-10:00 America/New_York only
- opening-forward +/-200 SPX points
- same pre-trade NBBO aggressor classifier
- same M+1 causal availability rule
- same Black-76 Greek calculations
- same hedge sign convention
- minimum classified-volume Greek coverage: 90%
- horizon: 15 minutes only

All authorized acquisition and all three local preparation pipelines completed before the dedicated Batch-5 validator was run once across the full frozen date set.

## Endpoint A — historical continuity

Endpoint A is the unchanged historical two-control architecture:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: `backward_return_1m_bps` and `flow_net_signed_contracts`
- statistic: rank-partial Spearman

| Trading day | Observations | Endpoint A partial Spearman | Negative sign |
|---|---:|---:|---|
| 2026-07-29 | 29 | +0.024628 | no |
| 2026-07-28 | 29 | +0.298508 | no |
| 2026-07-27 | 29 | -0.117435 | yes |

Endpoint A sign summary:

- days: 3
- negative days: **1 / 3 (33.3%)**
- median: **+0.024628**
- range: **-0.117435 to +0.298508**

**Result:** Endpoint A remains mixed/mostly positive and further weakens the historical two-control architecture. This does not reverse or repair the prior Batch-4 failure.

## Endpoint B — ordinary association stability / heterogeneity

Endpoint B remained unchanged:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: none
- statistic: ordinary Spearman

| Trading day | Observations | Endpoint B ordinary Spearman | Negative sign |
|---|---:|---:|---|
| 2026-07-29 | 29 | +0.000985 | no |
| 2026-07-28 | 29 | +0.130542 | no |
| 2026-07-27 | 29 | -0.194581 | yes |

Endpoint B sign summary:

- days: 3
- negative days: **1 / 3 (33.3%)**
- median: **+0.000985**
- range: **-0.194581 to +0.130542**

**Result:** Under the pre-specified Batch-5 interpretation, Endpoint B being negative on only 0-1 of 3 days materially weakens the idea that the negative ordinary association is even the dominant sign in nearby sessions. The result is not a clean validation and does not support a universal negative opening relationship.

2026-07-29 is effectively near zero rather than meaningful positive evidence; its exact frozen value remains +0.000985 and must not be relabeled negative. 2026-07-28 is a substantive positive session at +0.130542. 2026-07-27 is a substantive negative session at -0.194581.

## Frozen control diagnostics

| Trading day | Hedge partial \| momentum | Hedge partial \| raw | Hedge/raw | Hedge/momentum | Raw/momentum |
|---|---:|---:|---:|---:|---:|
| 2026-07-29 | +0.148334 | -0.118244 | -0.291626 | +0.393596 | +0.083744 |
| 2026-07-28 | +0.192501 | +0.228585 | -0.109852 | +0.396059 | -0.037438 |
| 2026-07-27 | -0.105754 | -0.174180 | +0.088177 | +0.629064 | +0.136453 |

These are required diagnostics, not alternate endpoints, and do not change the frozen adjudication.

Descriptively:

- **2026-07-29:** ordinary association is essentially zero (+0.000985). The momentum-only partial becomes positive (+0.148334), raw-only becomes negative (-0.118244), and the joint two-control residual is near zero positive (+0.024628). This is a control-sensitive near-zero session, not evidence for either universal sign.
- **2026-07-28:** ordinary association is positive (+0.130542), both single-control partials are positive, and Endpoint A is more positive (+0.298508). The positive sign is not created solely by the joint two-control residualization.
- **2026-07-27:** ordinary association is negative (-0.194581), both single-control partials remain negative, and Endpoint A remains negative (-0.117435).

## Data-quality diagnostics

| Trading day | Replay matches / opening rows | Median symbol-minute Greek solve rate | Median classified volume with Greeks |
|---|---:|---:|---:|
| 2026-07-29 | 30 / 30 | 98.63% | 99.93% |
| 2026-07-28 | 30 / 30 | 95.76% | 99.88% |
| 2026-07-27 | 30 / 30 | 95.58% | 99.70% |

All three sessions have complete 30/30 opening replay matching, high median Greek solve rates, and approximately 99.70%-99.93% median classified-volume Greek coverage. The mixed signs should therefore not be dismissed as an obvious replay or Greek-coverage failure.

## Interpretation against the frozen Batch-5 protocol

The protocol pre-specified:

- Endpoint B negative on all 3 days would strengthen evidence that the negative ordinary association is common;
- Endpoint B negative on 2/3 would repeat the Batch-4 qualitative pattern and support conditional heterogeneity;
- Endpoint B negative on only 0-1/3 would materially weaken the idea that the negative ordinary association is even the dominant sign in nearby sessions;
- Endpoint A remaining mixed or mostly positive would further weaken the historical two-control architecture.

Observed Batch-5 outcome:

- Endpoint A: **1/3 negative**, median +0.024628
- Endpoint B: **1/3 negative**, median +0.000985

Therefore Batch 5 **materially weakens both the historical two-control architecture and the idea that the negative ordinary opening-15m association is the dominant nearby-session sign**.

This strengthens the broader conclusion that the relationship is session-dependent and heterogeneous. It does not imply that the hedge proxy has no information, but it does rule against treating the current opening-15m relationship as a universal negative-sign production rule.

The previously inspected 8/8 ordinary-negative research pattern remains historically important but cannot be treated as out-of-sample evidence. Batch 4 prospectively produced 2/3 negative, including a broad positive reversal on 2026-07-31; Batch 5 now prospectively produces only 1/3 negative, with 2026-07-28 positive and 2026-07-29 essentially zero.

## Scientific limits

Do not change the sign convention, aggressor classifier, strike band, coverage floor, horizon, or window to improve this result.

Do not discard 2026-07-28 or relabel 2026-07-29 as negative. Do not let the negative 2026-07-27 session rescue the batch.

`hedge_delta_units` remains an opposite-side liquidity-provider/dealer-hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify customer/dealer inventory or executed underlying hedge trades. Correlation, partial correlation, sign stability, and any later influence diagnostic do not establish causality or a production trading edge.

## Next research rule

Do not immediately buy another batch to chase the same negative-sign hypothesis.

First perform only local, post-validation diagnostics under a separately frozen protocol to determine whether the substantive 2026-07-28 positive ordinary result is broad or influence-sensitive and whether the near-zero 2026-07-29 result is intrinsically unstable. Those diagnostics must not create a new regime filter or alter the official Batch-5 endpoints.
