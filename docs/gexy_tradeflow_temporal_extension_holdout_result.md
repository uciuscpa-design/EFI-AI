# GEXY temporal-extension holdout result

## Status

Official frozen holdout result recorded immediately after the first dedicated all-three-date reveal and before any post-hoc influence or alternative-specification analysis.

Reserved dates were revealed together in the frozen order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

The reveal used `scripts/gexy_tradeflow_temporal_extension_holdout_validator.py --reveal` after the holdout-safe preflight had passed.

## Frozen specification

- opening window: 09:30-10:00 America/New_York only;
- horizon: 15 minutes only;
- minimum classified-volume Greek coverage: 90%;
- signal: `hedge_delta_units`;
- primary target: `forward_return_15m_bps`;
- primary endpoint: ordinary Spearman correlation between signal and target;
- August reference median: -0.209360;
- no alternate threshold, window, horizon, sign convention, or sample repair authorized after reveal.

## Three untouched Endpoint-B results

| Trading day | Eligible observations | Endpoint B ordinary Spearman | Sign | LOO stability category | LOO same-sign | LOO range |
|---|---:|---:|---|---|---:|---|
| 2026-07-21 | 29 | -0.163547 | negative | strict_sign_stable_negative | 29/29 (100%) | -0.249589 to -0.070608 |
| 2026-07-20 | 29 | +0.157143 | positive | strict_sign_stable_positive | 29/29 (100%) | +0.090859 to +0.245211 |
| 2026-07-17 | 29 | +0.096059 | positive | strict_sign_stable_positive | 29/29 (100%) | +0.008210 to +0.179529 |

Endpoint A (historical two-control partial Spearman; continuity only) was:

- 2026-07-21: -0.246593
- 2026-07-20: +0.253737
- 2026-07-17: +0.155929

## Frozen temporal-extension adjudication

Three-day median Endpoint B:

- **+0.096059**

Frozen August reference median:

- **-0.209360**

Primary condition:

- holdout median > August reference median: **PASS**

Secondary sign composition:

- negative days: 1
- positive days: 2
- exact-zero days: 0
- strict sign-stable negative days: 1
- strict sign-stable positive days: 2
- sign-fragile days: 0

## Combined 20-session chronology

After appending the untouched dates before 2026-07-22 in chronological order, the combined 20-session ordinal-time Spearman was:

- **-0.393985**

Leave-one-day-out trend stability:

- 20/20 estimates retained the negative sign;
- same-sign percentage: 100%;
- LOO median: -0.380702;
- LOO range: -0.477193 to -0.321053;
- no opposite-sign LOO estimate.

Sign-run summary:

- sign runs: 8
- longest negative run: 9
- longest positive run: 2
- terminal run sign: negative
- terminal run length: 9

Frozen adjudication outcome:

- **TEMPORAL-EXTENSION SUPPORT**

This outcome follows the pre-specified rule because both conditions hold: the three-date holdout median is above -0.209360 and the combined 20-session chronological trend remains negative.

## Scientific interpretation

The untouched block supports the narrow descriptive claim that the later negative chronological clustering seen through August extends backward in the frozen manner specified by the protocol: the immediately preceding three-session block was, in aggregate, materially less negative/more positive than the August reference, while the full 20-session chronology retains a stable negative time trend.

This does **not** establish a persistent trading regime, statistical independence, causality, dealer inventory, executed dealer hedges, or a production trading edge. `hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy. No p-value or independence claim is authorized.

## Discipline after reveal

The holdout is now seen data. Any subsequent influence, regime, threshold, subwindow, feature, or alternative-specification analysis must be labeled post-hoc and may not retroactively alter this official frozen result.
