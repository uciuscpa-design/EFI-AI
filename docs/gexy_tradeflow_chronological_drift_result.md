# GEXY chronological drift characterization result

## Status

This document records the completed post-hoc descriptive chronological-drift characterization run under the frozen protocol.

Execution safeguards passed before the characterization:

- `tests/test_gexy_tradeflow_chronological_drift.py`
- result: `4 passed`
- code HEAD before execution: `8609d6e`

The characterization used only the 17 already-seen local development sessions, the unchanged opening 15-minute Endpoint-B construction, and the frozen 90% classified-volume Greek coverage floor. It made no market-data request and did not read the reserved holdout dates 2026-07-21, 2026-07-20, or 2026-07-17.

## Frozen scope

Dates analyzed oldest to newest:

1. 2026-07-22
2. 2026-07-23
3. 2026-07-24
4. 2026-07-27
5. 2026-07-28
6. 2026-07-29
7. 2026-07-30
8. 2026-07-31
9. 2026-08-03
10. 2026-08-04
11. 2026-08-05
12. 2026-08-06
13. 2026-08-07
14. 2026-08-10
15. 2026-08-11
16. 2026-08-12
17. 2026-08-13

The pasted terminal transcript omitted the visible day-table line for chronological index 7 / 2026-07-30, but downstream outputs confirm the computation itself included all 17 sessions: trend LOO count was 17, July contained 8 sessions, and multiple rolling windows explicitly include 2026-07-30. The cumulative characterization had already recorded 2026-07-30 ordinary Endpoint B = `-0.145813`, strict sign-stable negative.

## Ordinal-time trend

Full-sample Spearman between chronological index and ordinary Endpoint B:

- trend Spearman: **-0.306373**

Leave-one-day-out trend stability:

- LOO count: **17**
- same-sign count: **17 / 17**
- same-sign pct: **100%**
- LOO median: **-0.288235**
- LOO minimum: **-0.432353**
- LOO maximum: **-0.202941**
- any opposite-sign deletion: **false**

Under the frozen interpretation rule, this is descriptive evidence of a stable negative chronological tendency in the already-seen 17-day sample. It is not a significance test, stationarity proof, or forward predictor.

## Sign-run structure

- sign runs: **7**
- longest negative run: **9 sessions**
- longest positive run: **2 sessions**
- terminal run sign: **negative**
- terminal run length: **9 sessions**

The terminal negative run spans the available August block from 2026-08-03 through 2026-08-13.

## Fixed five-session rolling medians

The pre-specified trailing five-session rolling medians were:

| Window | Rolling median Endpoint B | Sign |
|---|---:|---|
| 2026-07-22 to 2026-07-28 | -0.123645 | negative |
| 2026-07-23 to 2026-07-29 | +0.000985 | positive |
| 2026-07-24 to 2026-07-30 | -0.123645 | negative |
| 2026-07-27 to 2026-07-31 | +0.000985 | positive |
| 2026-07-28 to 2026-08-03 | +0.000985 | positive |
| 2026-07-29 to 2026-08-04 | -0.136453 | negative |
| 2026-07-30 to 2026-08-05 | -0.145813 | negative |
| 2026-07-31 to 2026-08-06 | -0.209360 | negative |
| 2026-08-03 to 2026-08-07 | -0.356650 | negative |
| 2026-08-04 to 2026-08-10 | -0.356650 | negative |
| 2026-08-05 to 2026-08-11 | -0.209360 | negative |
| 2026-08-06 to 2026-08-12 | -0.209360 | negative |
| 2026-08-07 to 2026-08-13 | -0.144335 | negative |

After the 2026-07-29 to 2026-08-04 window, every subsequent five-session rolling median remained negative in this seen sample.

## Post-hoc July/August description

| Month | Days | Negative | Positive | Strict-stable negative | Strict-stable positive | Fragile | Median Endpoint B | Min | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-07 | 8 | 4 | 4 | 4 | 3 | 1 | -0.061330 | -0.230542 | +0.329557 |
| 2026-08 | 9 | 9 | 0 | 8 | 0 | 1 | -0.209360 | -0.486700 | -0.063547 |

The month split is explicitly post-hoc because the July/August contrast motivated the protocol. It must not be treated as a pre-specified calendar rule.

## Frozen adjudication

The result satisfies the protocol's descriptive nonstationarity condition:

- ordinal-time correlation is negative;
- all 17 leave-one-day-out trend estimates remain negative;
- the fixed rolling medians become persistently negative across the later windows;
- the sample ends with a nine-session negative run;
- all nine available August sessions have negative ordinary Endpoint B values.

Therefore the correct wording is:

**The already-seen 17-session sample shows meaningful temporal nonstationarity / chronological clustering in the opening 15-minute hedge-proxy/forward-return association.**

This does **not** establish that calendar time causes the relationship, that August is intrinsically a negative regime, that the pattern will persist, or that a calendar-based production rule is valid.

## Research implication

The evidence now supports two simultaneous statements:

1. broad positive and broad negative session-wide associations both recur under the unchanged construction;
2. those states are not randomly interleaved in this short seen sample; the later portion is strongly clustered negative.

The failed 09:40 six-descriptor screen means the project does not yet have a prospectively validated way to identify the state early in the session.

Before spending on another historical backfill, the next validation design should focus on forward temporal persistence and state identification rather than another retrospective sign-count batch.

## Scientific limits

All 17 sessions were already-seen development data. The chronology test and month split are descriptive and post-hoc. The sample is short and contiguous. The 15-minute forward-return labels overlap at the minute level. `hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy, not observed dealer inventory or executed hedge flow.

No causal, statistical-stationarity, or production-edge claim is supported by this result.
