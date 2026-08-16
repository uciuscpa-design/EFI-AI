# GEXY opening-window validation Batch 6 result

## Status

This document records the fresh untouched Batch-6 heterogeneity-replication result after the protocol, dates/order, acquisition scope, 15-minute horizon, 90% classified-volume Greek coverage floor, Endpoint A, and Endpoint B were fixed before endpoint inspection.

Frozen dates, in order:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

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

All authorized acquisition and all three local preparation pipelines completed before the dedicated Batch-6 validator was run once across the full frozen date set. The safeguard suite passed 4/4 immediately before the reveal after a narrow CLI help-text repair that did not change endpoint math or sample construction.

## Endpoint A — historical continuity

Endpoint A remained the historical two-control architecture:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: `backward_return_1m_bps` and `flow_net_signed_contracts`
- statistic: rank-partial Spearman

| Trading day | Observations | Endpoint A partial Spearman | Sign |
|---|---:|---:|---|
| 2026-07-24 | 29 | -0.109626 | negative |
| 2026-07-23 | 29 | +0.299817 | positive |
| 2026-07-22 | 29 | -0.120838 | negative |

Endpoint A summary:

- days: 3
- negative days: **2 / 3**
- positive days: **1 / 3**
- exact-zero days: **0 / 3**
- median: **-0.109626**
- range: **-0.120838 to +0.299817**

**Result:** Endpoint A remains heterogeneous. Two negative days do not restore the historical two-control architecture because the same untouched batch contains a large positive day (+0.299817), and prior Batch-4/5 failures remain part of the cumulative record.

## Endpoint B — ordinary heterogeneity endpoint

Endpoint B remained unchanged:

- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- controls: none
- statistic: ordinary Spearman
- interpretation: heterogeneity endpoint with no assumed dominant sign

| Trading day | Observations | Endpoint B ordinary Spearman | Sign |
|---|---:|---:|---|
| 2026-07-24 | 29 | -0.123645 | negative |
| 2026-07-23 | 29 | +0.329557 | positive |
| 2026-07-22 | 29 | -0.230542 | negative |

Endpoint B summary:

- days: 3
- negative days: **2 / 3**
- positive days: **1 / 3**
- exact-zero days: **0 / 3**
- median: **-0.123645**
- range: **-0.230542 to +0.329557**

**Result:** Mixed signs directly replicate cross-session sign heterogeneity under the unchanged construction, exactly as specified in the Batch-6 protocol. The positive 2026-07-23 session is larger in absolute value than either negative day, so the batch must not be summarized as a simple negative-sign win. It also does not erase prior broad positive, broad negative, or near-zero sessions.

## Frozen control diagnostics

| Trading day | Hedge partial \| momentum | Hedge partial \| raw | Hedge/raw | Hedge/momentum | Raw/momentum |
|---|---:|---:|---:|---:|---:|
| 2026-07-24 | -0.048996 | -0.176446 | +0.288670 | +0.466995 | -0.092611 |
| 2026-07-23 | +0.352678 | +0.269725 | -0.319704 | +0.262562 | -0.249754 |
| 2026-07-22 | -0.089352 | -0.264780 | +0.165517 | +0.516256 | +0.093596 |

These are required diagnostics, not alternate endpoints, and do not change the frozen adjudication.

Descriptively:

- **2026-07-24:** ordinary association is negative and remains negative after each single control; the two-control endpoint is also negative.
- **2026-07-23:** ordinary association is strongly positive and remains positive after momentum-only, raw-only, and joint-control residualization.
- **2026-07-22:** ordinary association is negative and remains negative after each single control and after both controls.

This pattern makes 2026-07-23 particularly important: its positive sign is not created solely by the joint two-control residualization.

## Data-quality diagnostics

| Trading day | Replay matches / opening rows | Median symbol-minute Greek solve rate | Median classified volume with Greeks |
|---|---:|---:|---:|
| 2026-07-24 | 30 / 30 | 95.41% | 99.74% |
| 2026-07-23 | 30 / 30 | 96.11% | 99.72% |
| 2026-07-22 | 30 / 30 | 96.51% | 99.61% |

All three sessions have complete 30/30 opening replay matching, strong Greek solve rates, and approximately 99.61%-99.74% median classified-volume Greek coverage. The mixed signs therefore should not be dismissed as an obvious replay or Greek-coverage failure.

## Interpretation against the frozen Batch-6 protocol

The protocol pre-specified that mixed Endpoint-B signs across the three untouched days would directly replicate cross-session sign heterogeneity under the unchanged construction.

Observed Batch-6 outcome:

- Endpoint A: **2 negative / 1 positive**, median -0.109626
- Endpoint B: **2 negative / 1 positive**, median -0.123645
- largest absolute Endpoint-B value: **+0.329557 on 2026-07-23**

Therefore Batch 6 is a **direct heterogeneity replication**. It does not restore a universal negative relationship and does not justify a directional production rule. The unchanged construction continues to produce materially positive and materially negative sessions.

## Scientific limits

Do not change the sign convention, aggressor classifier, strike band, coverage floor, horizon, window, or controls to improve this result.

Do not discard 2026-07-23 because it conflicts with a negative-sign narrative, and do not let the two negative sessions erase prior broad positive or near-zero sessions.

`hedge_delta_units` remains an opposite-side liquidity-provider/dealer-hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify customer/dealer inventory or executed underlying hedge trades. Correlation, partial correlation, sign stability, heterogeneity, and any later influence diagnostic do not establish causality or a production trading edge.

## Next research rule

Before buying another batch, perform only a separately frozen local post-validation influence audit on the same Batch-6 sample. The audit may ask whether 2026-07-23's positive association and the two negative sessions are broad or concentrated in a small number of observations. It may not create a regime classifier, alter official endpoints, remove observations, or introduce new horizons/signals.
