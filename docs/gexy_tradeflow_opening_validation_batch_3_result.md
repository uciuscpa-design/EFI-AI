# GEXY opening-window validation batch 3 result

## Status

This document records the untouched opening-window validation of the post-batch time-of-day hypothesis. The candidate rule, dates, data scope, and endpoints were frozen before batch-3 TCBBO was purchased or inspected.

Validation dates, in frozen order:

1. 2026-08-06
2. 2026-08-05
3. 2026-08-04

Frozen scope:

- SPXW 0DTE TCBBO
- 09:30-10:00 America/New_York only
- opening-forward +/-200 SPX points
- frozen pre-trade NBBO aggressor classifier
- M+1 causal availability
- Black-76 Greek weighting
- 90% classified-volume Greek coverage floor
- unchanged hedge sign convention

No batch-3 endpoint was inspected before all three acquisitions were completed.

## Primary endpoint — opening 15 minutes

The pre-specified primary endpoint is `net_contracts_vs_delta`: `hedge_delta_units` versus 15-minute forward SPX return using rank-partial Spearman while controlling for `backward_return_1m_bps` and `flow_net_signed_contracts`. The research-set expected sign was negative.

| Trading day | Observations | Momentum Spearman | Raw partial Spearman controlling momentum | Hedge Spearman | Hedge partial Spearman controlling momentum + raw | Negative sign |
|---|---:|---:|---:|---:|---:|---|
| 2026-08-06 | 29 | -0.193103 | -0.553123 | -0.209360 | +0.121166 | no |
| 2026-08-05 | 29 | -0.271429 | +0.359105 | -0.486700 | -0.522197 | yes |
| 2026-08-04 | 29 | -0.308374 | +0.312136 | -0.418719 | -0.436355 | yes |

Primary sign-stability summary:

- days: 3
- negative days: 2 / 3 (66.7%)
- median partial Spearman: **-0.436355**
- range: **-0.522197 to +0.121166**

Descriptive pooled opening result with categorical day fixed effects:

- observations: 87 across 3 days
- partial Spearman controlling momentum, raw flow, and day fixed effects: **-0.221508**

## Secondary endpoint — opening 5 minutes

The pre-specified secondary endpoint uses the same net-delta signal and controls at a 5-minute horizon.

| Trading day | Observations | Momentum Spearman | Raw partial Spearman controlling momentum | Hedge Spearman | Hedge partial Spearman controlling momentum + raw | Negative sign |
|---|---:|---:|---:|---:|---:|---|
| 2026-08-06 | 29 | -0.225123 | -0.185585 | -0.016256 | +0.175254 | no |
| 2026-08-05 | 29 | -0.088177 | +0.027073 | -0.248276 | -0.238513 | yes |
| 2026-08-04 | 29 | -0.194581 | +0.073818 | -0.375862 | -0.380469 | yes |

Secondary sign-stability summary:

- negative days: 2 / 3 (66.7%)
- median partial Spearman: **-0.238513**
- range: **-0.380469 to +0.175254**

Descriptive pooled opening 5-minute result with categorical day fixed effects:

- observations: 87 across 3 days
- partial Spearman: **-0.208903**

## Interpretation

Batch 3 provides **partial replication** of the opening-window hypothesis, not a clean universal validation.

The primary 15-minute endpoint retained the expected negative sign on two of three untouched sessions, with large negative residual associations on 2026-08-05 and 2026-08-04. However, 2026-08-06 reversed sign to +0.121166. The pooled descriptive estimate remains negative, but the failed day is substantive evidence against a universal opening-window effect and must not be discarded or reclassified after the fact.

The secondary 5-minute endpoint shows the same qualitative pattern: negative on 2026-08-05 and 2026-08-04, positive on 2026-08-06. It therefore does not supply an independent rescue of the primary failure.

The correct current statement is that the opening-window net-delta residual association remains a plausible conditional tendency, especially at 15 minutes, but it is not yet stable enough to call a validated mechanism or production signal.

The raw-flow control also varies strongly across dates, while the Greek-weighted residual changes sign on 2026-08-06. This reinforces the need to understand whether the failed day reflects data-quality limitations or genuine market-regime heterogeneity before any new rule is proposed.

No causal claim is established. OPRA does not identify dealer inventory or executed underlying hedge trades; `hedge_delta_units` remains a proxy.

## Post-validation quality audit

A local-only quality audit was run after recording the validation result. It did not alter or re-score the frozen endpoint.

Across all three validation dates, the local causal files show 30 common timestamps and 30/30 replay-matched timestamps. Median symbol-minute Greek solve rates were 97.4% on 2026-08-06, 98.9% on 2026-08-05, and 97.9% on 2026-08-04. Median classified contract volume with usable Greeks was 99.9%, 100.0%, and 100.0%, respectively.

Therefore the positive 2026-08-06 residual should **not** be attributed to an obvious replay or Greek-coverage failure. The quality metrics are comparable to the two successful negative-sign days.

A second diagnostic clue is that the ordinary 15-minute `hedge_delta_units` association on 2026-08-06 remained negative (-0.209360), while the frozen residual after controlling momentum and raw flow was positive (+0.121166). This means the validation failure occurs in the incremental information after controls rather than in the raw direction of the Greek-weighted hedge proxy itself.

The next local-only audit should therefore examine control structure—especially rank correlation among `hedge_delta_units`, `flow_net_signed_contracts`, and `backward_return_1m_bps`, and how the hedge/target association changes when controlling momentum only, raw flow only, and both. This is a statistical diagnostic, not a new signal-selection exercise.

## Next rule

Do not tune the signal, coverage floor, horizon, aggressor classifier, strike band, or sign convention in response to the failed 2026-08-06 session.

Treat 2026-08-06 as genuine observed heterogeneity unless a pre-specified statistical-control audit demonstrates that the positive residual is primarily a suppression/collinearity artifact. Even then, do not remove or relabel the day from batch-3 validation.

Do not purchase more TCBBO until the control-structure audit is complete. Any future regime hypothesis must be frozen separately before acquiring new untouched data.