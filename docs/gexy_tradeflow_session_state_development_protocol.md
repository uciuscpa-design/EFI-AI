# GEXY opening session-state development protocol

## Status and purpose

This protocol is frozen after the Batch-6 validation and its separately frozen influence audit are complete, and before any session-state feature screen is run.

The cumulative evidence no longer supports a universal or consistently dominant sign for the opening 15-minute `hedge_delta_units` / forward-return relationship. Under the unchanged construction, broad positive, broad negative, and near-zero/sign-fragile sessions have all been observed.

The next research question is therefore:

> Can a small, prospectively available early-opening state descriptor anticipate the later day-level sign/magnitude of the frozen ordinary opening-15m relationship?

This is a **development-only** phase. Every date used below has already been inspected in earlier research. No result from these dates may be described as out-of-sample validation or production evidence.

## Development dates

Use exactly the complete already-seen opening sessions for which the unchanged local trade-flow / replay construction exists:

1. 2026-08-13
2. 2026-08-12
3. 2026-08-11
4. 2026-08-10
5. 2026-08-07
6. 2026-08-06
7. 2026-08-05
8. 2026-08-04
9. 2026-08-03
10. 2026-07-31
11. 2026-07-30
12. 2026-07-29
13. 2026-07-28
14. 2026-07-27
15. 2026-07-24
16. 2026-07-23
17. 2026-07-22

No date may be removed because of its sign, magnitude, control sensitivity, or influence result. If a required local file is technically unavailable, report that failure and stop rather than silently substituting another date.

## Reserved untouched holdout block

The next three prior trading sessions are reserved now and must not be used in development:

1. **2026-07-21**
2. **2026-07-20**
3. **2026-07-17**

Do not inspect, price for endpoint-driven reasons, or use these dates to choose a state descriptor. If development produces a candidate that satisfies the frozen selection rule below, a separate holdout acquisition/validation protocol must be recorded before any paid data request for these dates.

If no candidate satisfies the development rule, do not force a holdout test merely to continue the pipeline.

## Frozen outcome label

For each development day, use the already-defined Endpoint B value:

- ordinary Spearman correlation between `hedge_delta_units` and `forward_return_15m_bps`
- same opening 09:30-10:00 America/New_York sample
- same 90% classified-volume Greek coverage floor
- same M+1 causal feature timing

Use the **continuous Endpoint-B Spearman value** as the primary development target. Day sign is descriptive only. Do not create a post-hoc near-zero threshold.

## Prospective information cutoff

All candidate state descriptors must be computable by **09:40 America/New_York** using only completed information available at or before that timestamp.

Because trade-flow features use the frozen M+1 convention, the 09:40 state may use completed flow minutes through 09:39, but may not use any trade from the still-forming 09:40 minute.

No forward return label, post-09:40 trade flow, post-09:40 hedge flow, or full-window correlation may enter a state descriptor.

## Frozen candidate descriptor set

Compute exactly these six early-opening descriptors from timestamps 09:31 through 09:40 inclusive on the causal feature/replay rows.

### 1. Early forward return

`early_forward_return_bps`

- first valid `forward` in the early window to last valid `forward` in the early window
- report in basis points

### 2. Early hedge-delta imbalance

`early_hedge_delta_imbalance`

- numerator: sum of `hedge_delta_notional`
- denominator: sum of `hedge_gross_abs_delta_notional`
- ratio is undefined if denominator is zero

### 3. Early raw contract imbalance

`early_raw_contract_imbalance`

- numerator: sum of `flow_net_signed_contracts`
- denominator: sum of `flow_classified_contract_volume`
- ratio is undefined if denominator is zero

### 4. Early hedge-GEX imbalance

`early_hedge_gex_imbalance`

- numerator: sum of `hedge_gex_notional_per_1pct`
- denominator: sum of `hedge_gross_abs_gex_notional_per_1pct`
- ratio is undefined if denominator is zero

### 5. Early classified contract volume

`early_classified_contract_volume`

- sum of `flow_classified_contract_volume`
- no sign transformation or thresholding

### 6. Early gross hedge-delta activity

`early_gross_abs_delta_notional`

- sum of `hedge_gross_abs_delta_notional`
- no sign transformation or thresholding

Do not add call/put decomposition, volatility fields, alternate cutoffs, alternate windows, alternate horizons, GAX variants, wall distances, day-of-week, date trend, or externally sourced regime variables in this first screen.

## Frozen analysis

For each of the six descriptors:

1. report all 17 day-level descriptor values alongside the continuous Endpoint-B value;
2. compute Spearman correlation between the descriptor and Endpoint B across days;
3. compute 17 leave-one-day-out Spearman estimates;
4. report LOO median, min, max, sign-consistency count, and whether any deletion flips the full-sample sign;
5. report the number of finite day pairs used.

This is a development screen, not a statistical significance test. Do not convert the six correlations into causal claims or p-value-based discovery claims.

## Frozen candidate selection rule

At most **one** descriptor may advance to untouched holdout.

A descriptor is eligible only if all of the following are true:

1. at least 15 of 17 development dates have finite descriptor/target pairs;
2. absolute full-sample Spearman correlation with Endpoint B is at least **0.35**;
3. at least **80%** of finite leave-one-day-out estimates retain the full-sample correlation sign;
4. the full-sample sign is not reversed by deletion of any one day if there are at least 16 finite LOO estimates.

If more than one descriptor is eligible, select the one with the largest absolute full-sample Spearman correlation. Report all six results so the multiple-candidate development search remains visible.

If no descriptor is eligible, record **no candidate**. Do not lower thresholds, change the 09:40 cutoff, add features, or combine descriptors after seeing the screen.

No two-feature or multivariable model is permitted in this protocol.

## Holdout rule if a candidate emerges

If exactly one candidate is selected under the rule above:

- freeze the descriptor name and expected monotonic sign exactly as developed;
- do not fit a binary sign threshold on the development dates;
- evaluate the continuous descriptor versus continuous Endpoint-B value on the reserved untouched block under a separately frozen protocol;
- preserve all three holdout dates regardless of sign or quality unless a pre-defined technical availability rule requires a visible skip.

A three-day holdout will be small and descriptive. It may provide directional consistency evidence, but cannot by itself establish a deployable regime classifier.

## Cost and execution rule

This development screen must be **local-only / $0** and use already existing feature/replay files. It must make no Databento request.

Do not purchase the reserved holdout block until the development result is permanently recorded and a separate holdout protocol/cost plan is frozen.

## Implementation checkpoint

The protocol was implemented only after the rules above were frozen.

Dedicated screen:

- `scripts/gexy_tradeflow_session_state_development.py`
- implementation commit: `9eb096fa1f0a8980fa88d793a3d53b1ce9ddf3b4`

Safeguards:

- `tests/test_gexy_tradeflow_session_state_development.py`
- safeguard commit: `80d7eaaf8801933f40b42065acc392eb72a7bf1b`

The implementation hard-codes the 17 development dates and the three reserved holdout dates, uses the frozen 90% opening sample, filters causal timestamps to 09:31-09:40 America/New_York, computes exactly the six descriptors above, performs only the frozen univariate/leave-one-day-out screen, and selects at most one eligible candidate. The reserved holdout dates are never read by the script.

## Scientific limits

This protocol is explicitly exploratory development on already-seen data. It is designed to reduce—not eliminate—regime-search overfitting by fixing the early cutoff, descriptor list, analysis, and selection rule before the screen.

`hedge_delta_units` remains an inferred liquidity-provider/dealer-hedge proxy. OPRA does not identify dealer inventory or executed underlying hedges. A development correlation between an early state descriptor and a later session-level association does not establish causality, market mechanism, or production trading edge.
