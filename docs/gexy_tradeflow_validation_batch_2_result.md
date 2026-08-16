# GEXY trade-flow validation batch 2 result

## Status

This document records the fixed-endpoint five-day result after completing the pre-specified batch-2 validation sessions. The data scope, aggressor classifier, M+1 timing, Black-76 Greek calculations, 90% classified-volume Greek coverage floor, and primary endpoints were not changed in response to batch-2 results.

Evidence set:

- 2026-08-12: discovery
- 2026-08-13: first holdout
- 2026-08-11, 2026-08-10, 2026-08-07: pre-committed batch-2 validation dates

## Fixed primary endpoints

The fixed pair remains `net_contracts_vs_delta`. The primary statistic is `hedge_delta_units` rank-partial Spearman versus forward SPX return after controlling for:

1. `backward_return_1m_bps`, and
2. `flow_net_signed_contracts`.

Primary horizons remain 5 and 15 minutes.

## Day-by-day results

| Trading day | Horizon | Observations | Momentum Spearman | Raw partial Spearman controlling momentum | Hedge partial Spearman controlling momentum + raw |
|---|---:|---:|---:|---:|---:|
| 2026-08-07 | 5m | 53 | -0.300200 | -0.034336 | +0.026456 |
| 2026-08-07 | 15m | 43 | -0.203111 | -0.172684 | -0.250764 |
| 2026-08-10 | 5m | 52 | -0.115086 | +0.093070 | +0.035182 |
| 2026-08-10 | 15m | 42 | -0.070578 | -0.069736 | -0.162204 |
| 2026-08-11 | 5m | 53 | +0.156588 | -0.011273 | +0.109709 |
| 2026-08-11 | 15m | 43 | -0.088493 | -0.015986 | +0.022534 |
| 2026-08-12 | 5m | 51 | -0.324344 | +0.108631 | -0.199737 |
| 2026-08-12 | 15m | 42 | -0.053561 | -0.018426 | -0.251894 |
| 2026-08-13 | 5m | 51 | +0.149412 | -0.338274 | -0.182983 |
| 2026-08-13 | 15m | 41 | +0.222648 | -0.495672 | -0.203228 |

## Sign stability

### 5-minute endpoint

- negative days: 2 / 5 (40%)
- median partial Spearman: +0.026456
- range: -0.199737 to +0.109709
- all days negative: no

The initial negative 5-minute relationship does **not** generalize across the five-day evidence set. Three of the three new batch-2 dates are positive, although two are close to zero. The five-day median is slightly positive. This is evidence against treating the unconditional 5-minute negative relationship as a stable universal effect.

### 15-minute endpoint

- negative days: 4 / 5 (80%)
- median partial Spearman: -0.203228
- range: -0.251894 to +0.022534
- all days negative: no

The 15-minute endpoint is substantially more stable day-by-day than the 5-minute endpoint. Four of five days are negative and the lone positive day, 2026-08-11, is small (+0.022534). With only five days this is still insufficient for a claim of statistical reliability or production edge.

## Corrected post-holdout non-overlapping sensitivity

Code review after the first five-day run found that the pooling implementation controlled for a single ordinal `day_index` rather than true categorical day fixed effects. That implementation was corrected before interpreting the pooled result further. The day-by-day primary endpoints above were unaffected.

After re-running the same five local sessions with true categorical day fixed effects:

- 5m: 50 deterministic non-overlapping observations across 5 days; partial Spearman controlling momentum, raw flow, and day fixed effects = **-0.183525**.
- 15m: 10 deterministic non-overlapping observations across 5 days; corresponding partial Spearman = **+0.381954**.

Interpretation:

- The 5-minute non-overlapping sensitivity remains modestly negative even though the full-minute day-by-day endpoint is not sign-stable. This suggests any 5-minute structure is not a simple universal day-level effect.
- The 15-minute non-overlapping pooled estimate changes sign relative to the 4/5 negative day-level result. With only 10 controlled observations, this is too small to overturn the day-by-day evidence, but it is strong evidence that the 15-minute association is not uniform across the sampled intraday minutes/windows.
- Neither pooled sensitivity should be promoted to a primary result; both are post-holdout diagnostics with small effective sample sizes.

## Current verdict

Supported:

- The 15-minute fixed net-delta endpoint shows meaningful day-level negative sign stability across the five-day evidence set (4/5 negative; median about -0.203).
- The original 2026-08-13 holdout remains a valid same-sign replication of the 2026-08-12 discovery day.

Not supported:

- A universal negative 5-minute endpoint; batch 2 reverses/collapses it on all three new dates.
- A uniform 15-minute effect across all intraday observations; the corrected non-overlap sensitivity is opposite-signed and very small-sample.
- A claim that either horizon is statistically established with only five sessions.
- Causality from dealer hedging to SPX movement.
- A production trading edge.

## Next rule

Do not buy more TCBBO yet. Use the already purchased five sessions for explicitly post-batch exploratory analysis of time-window/regime dependence while keeping the original endpoint definition unchanged. The first exploratory split should be the two pre-existing acquisition windows (09:30-10:00 and 15:30-16:00 America/New_York), because this tests whether the contradictory pooled 15-minute result is concentrated by time of day without inventing a new signal. Do not tune the aggressor classifier, reverse the hedge sign convention, or silently redefine the original primary endpoints. Any newly proposed conditional rule must be frozen and validated on later untouched data before being called out-of-sample.
