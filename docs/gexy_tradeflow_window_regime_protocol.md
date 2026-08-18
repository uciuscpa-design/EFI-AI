# GEXY post-batch time-window exploration protocol

## Status

This is an explicitly **post-batch exploratory** analysis using the already purchased five-session evidence set. It is not an out-of-sample validation and must not be described as one.

The five-day unconditional fixed-endpoint result is already complete:

- 5-minute net-delta partial endpoint: 2/5 days negative; median +0.026456.
- 15-minute net-delta partial endpoint: 4/5 days negative; median -0.203228.
- Corrected deterministic non-overlap sensitivity with categorical day fixed effects: 5m -0.183525 on 50 observations; 15m +0.381954 on 10 observations.

The contradiction between the 15-minute day-level sign stability and the very small non-overlapping pooled sample motivates a time-of-day diagnostic before any additional TCBBO purchase.

## Frozen exploratory question

Does the **same unchanged net-delta endpoint** behave differently in the two acquisition windows that were already fixed before the TCBBO was purchased?

Analyze both windows without selecting one in advance:

1. opening: 09:30-10:00 America/New_York flow minutes
2. closing: 15:30-16:00 America/New_York flow minutes

Use all five existing dates:

- 2026-08-07
- 2026-08-10
- 2026-08-11
- 2026-08-12
- 2026-08-13

## Unchanged endpoint and controls

Keep exactly:

- hedge signal: `hedge_delta_units`
- raw control signal: `flow_net_signed_contracts`
- momentum control: `backward_return_1m_bps`
- horizons: 5 and 15 minutes
- classified-volume Greek coverage floor: 90%
- M+1 causal timing
- frozen aggressor classifier
- frozen Black-76 Greek calculations and hedge sign convention

No new signal family, call/put selection, threshold, strike filter, coverage floor, or horizon may replace these during this diagnostic.

## Reporting

Report:

1. day-by-day endpoint for every date, window, and horizon,
2. sign-stability summary separately for opening and closing windows,
3. pooled opening and closing endpoint with momentum, raw flow, and categorical day fixed effects.

Do not omit unfavorable cells or choose the stronger window after viewing results.

## Interpretation

This analysis may identify a candidate conditional regime, but any such regime is discovered on research data already used in prior diagnostics. It cannot establish a trading rule. If a window-specific pattern appears coherent enough to pursue, freeze it first and validate it on later untouched TCBBO before treating it as out-of-sample evidence.

No additional market-data purchase is authorized or needed for this diagnostic.
