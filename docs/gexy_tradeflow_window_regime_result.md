# GEXY post-batch time-window exploration result

## Status

This document records the explicitly post-batch exploratory time-window diagnostic run on the five already-purchased sessions. It is not an out-of-sample validation. The exploratory question and reporting rules were frozen before the output was viewed.

Dates:

- 2026-08-07
- 2026-08-10
- 2026-08-11
- 2026-08-12
- 2026-08-13

Windows:

- opening: 09:30-10:00 America/New_York
- closing: 15:30-16:00 America/New_York

The endpoint definition remained unchanged:

- hedge signal: `hedge_delta_units`
- momentum control: `backward_return_1m_bps`
- raw-flow control: `flow_net_signed_contracts`
- horizons: 5 and 15 minutes
- classified-volume Greek coverage floor: 90%
- M+1 causal timing
- frozen aggressor classifier, Greek calculations, and hedge sign convention

## Day-by-day results

| Trading day | Window | Horizon | Observations | Hedge partial Spearman controlling momentum + raw |
|---|---|---:|---:|---:|
| 2026-08-07 | opening | 5m | 29 | -0.034785 |
| 2026-08-07 | opening | 15m | 29 | -0.118163 |
| 2026-08-07 | closing | 5m | 24 | +0.087410 |
| 2026-08-07 | closing | 15m | 14 | +0.382527 |
| 2026-08-10 | opening | 5m | 29 | -0.380904 |
| 2026-08-10 | opening | 15m | 29 | -0.415499 |
| 2026-08-10 | closing | 5m | 23 | +0.086384 |
| 2026-08-10 | closing | 15m | 13 | +0.283878 |
| 2026-08-11 | opening | 5m | 29 | -0.083573 |
| 2026-08-11 | opening | 15m | 29 | -0.114670 |
| 2026-08-11 | closing | 5m | 24 | +0.007628 |
| 2026-08-11 | closing | 15m | 14 | -0.051536 |
| 2026-08-12 | opening | 5m | 29 | -0.202389 |
| 2026-08-12 | opening | 15m | 29 | -0.403520 |
| 2026-08-12 | closing | 5m | 22 | -0.362291 |
| 2026-08-12 | closing | 15m | 13 | +0.524508 |
| 2026-08-13 | opening | 5m | 29 | -0.000716 |
| 2026-08-13 | opening | 15m | 29 | -0.146997 |
| 2026-08-13 | closing | 5m | 22 | -0.287750 |
| 2026-08-13 | closing | 15m | 12 | +0.230594 |

## Sign-stability summary

### Opening window

5-minute endpoint:

- negative days: 5 / 5
- median partial Spearman: -0.083573
- range: -0.380904 to -0.000716
- pooled partial Spearman with categorical day fixed effects: -0.063238 on 145 observations

15-minute endpoint:

- negative days: 5 / 5
- median partial Spearman: -0.146997
- range: -0.415499 to -0.114670
- pooled partial Spearman with categorical day fixed effects: -0.185457 on 145 observations

### Closing window

5-minute endpoint:

- negative days: 2 / 5
- median partial Spearman: +0.007628
- range: -0.362291 to +0.087410
- pooled partial Spearman with categorical day fixed effects: -0.056225 on 115 observations

15-minute endpoint:

- negative days: 1 / 5
- median partial Spearman: +0.283878
- range: -0.051536 to +0.524508
- pooled partial Spearman with categorical day fixed effects: +0.179066 on 66 observations

## Interpretation

The exploratory split reveals strong time-of-day heterogeneity.

The opening 15-minute endpoint is the clearest candidate conditional relationship in the current data: all five sessions are negative and the pooled day-fixed-effect estimate is also negative. The closing 15-minute endpoint is largely opposite-signed, with four of five sessions positive and a positive pooled estimate.

The opening 5-minute endpoint is also negative on all five sessions, but its median and pooled magnitudes are materially weaker than the opening 15-minute endpoint. It should remain secondary rather than replacing the 15-minute candidate because it is a weaker post-batch discovery.

This time-window rule was discovered after examining the five-session research set. It is therefore exploratory and cannot be described as validated or out-of-sample. The contrast is nevertheless a plausible explanation for why the unconditional 15-minute day-level result and the non-overlapping pooled sensitivity gave contradictory signs.

No causal claim is established. OPRA still does not identify dealer inventory or executed underlying hedge trades.

## Next rule

Freeze a new untouched validation protocol before pricing or downloading more TCBBO. The candidate primary endpoint should be the unchanged 15-minute `net_contracts_vs_delta` partial Spearman restricted to the opening 09:30-10:00 America/New_York window, using the same controls and 90% Greek-volume coverage floor. The opening 5-minute endpoint may be reported as a pre-specified secondary endpoint.

Do not use the closing-window result as an inverse trading rule unless such a rule is separately frozen and validated on untouched data.
