# GEXY two-day fixed-endpoint stability — 2026-08-12 and 2026-08-13

## Status

This document records the post-holdout stability analysis using the already frozen primary endpoint definition. It does not introduce a new signal, change the aggressor classifier, reverse the hedge sign convention, or alter the 90% classified-volume Greek coverage floor.

## Fixed primary endpoints

The fixed pair remains `net_contracts_vs_delta`. The reported statistic is `hedge_delta_units` rank-partial Spearman versus forward SPX return after controlling for:

1. `backward_return_1m_bps`, and
2. `flow_net_signed_contracts`.

Primary horizons remain 5 and 15 minutes.

## Day-by-day results

| Trading day | Horizon | Observations | Momentum Spearman | Raw partial Spearman controlling momentum | Hedge partial Spearman controlling momentum + raw |
|---|---:|---:|---:|---:|---:|
| 2026-08-12 | 5m | 51 | -0.324344 | +0.108631 | -0.199737 |
| 2026-08-12 | 15m | 42 | -0.053561 | -0.018426 | -0.251894 |
| 2026-08-13 | 5m | 51 | +0.149412 | -0.338274 | -0.182983 |
| 2026-08-13 | 15m | 41 | +0.222648 | -0.495672 | -0.203228 |

## Sign stability

### 5-minute endpoint

- negative days: 2 / 2
- median partial Spearman: -0.191360
- range: -0.199737 to -0.182983
- all observed days negative: yes

### 15-minute endpoint

- negative days: 2 / 2
- median partial Spearman: -0.227561
- range: -0.251894 to -0.203228
- all observed days negative: yes

The two-day day-level result therefore shows stable negative sign and fairly similar magnitude at both fixed primary horizons. Two days are not enough to claim statistical reliability or a production trading edge.

## Deterministic non-overlapping sensitivity

A post-holdout sensitivity used deterministic clock-spaced observations to reduce forward-return overlap while retaining the same fixed endpoint and controls.

- 5-minute horizon: 20 observations across 2 days; partial Spearman controlling momentum, raw flow, and day = **-0.61458**.
- 15-minute horizon: 4 observations across 2 days; partial Spearman is undefined (`NaN`) because the sample is too small for the controlled statistic.

Interpretation:

- The 5-minute negative relationship survives a simple non-overlapping sensitivity and is stronger in this very small subset. This is encouraging but the 20-observation sample is too small for strong inference.
- The 15-minute non-overlapping sensitivity is **inconclusive**, not negative evidence. Four observations do not support the controlled correlation calculation.

## Current evidence state

Supported so far:

- The fixed 5-minute net-delta partial relationship is negative on both the discovery and first holdout day.
- The fixed 15-minute net-delta partial relationship is negative on both days.
- The 5-minute sign also survives a deterministic non-overlapping post-holdout sensitivity.

Not established:

- statistical significance under dependence-aware inference,
- causality from dealer hedging to SPX movement,
- stable call-versus-put decomposition,
- superiority of Greek weighting over raw flow on every day,
- production trading profitability.

## Next validation rule

Do not change the signal definition before the next untouched TCBBO validation day. The next validation should continue to report the same two primary endpoints first: 5-minute and 15-minute `net_contracts_vs_delta` partial Spearman after the same two controls and the same 90% Greek-volume coverage floor.

Before buying more TCBBO, use metadata-only cost estimation. No additional data should be purchased merely to tune the existing signal. A future changed mechanism must be frozen first and validated on data not used to design it.
