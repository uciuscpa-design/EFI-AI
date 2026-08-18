# GEXY session-state development pre-screen repair checkpoint

## Status

This checkpoint records a fail-closed implementation repair before any session-state development correlations or candidate-selection results were produced.

The frozen development protocol remains unchanged. The 17 development dates, reserved holdout dates, 09:40 causal cutoff, six descriptors, continuous Endpoint-B target, selection thresholds, and holdout rules are unchanged.

## First execution attempt

The safeguard suite passed 3/3 before the first execution attempt.

The development script then aborted during descriptor construction with:

`ValueError: early state frame missing required column: flow_classified_contract_volume`

The failure occurred before the day-level development table, six-descriptor screen, Spearman correlations, leave-one-day-out results, eligibility flags, or selected candidate were printed or written as a completed screen result.

No reserved holdout date was read and no market-data request was made.

## Root cause

The development wrapper obtains the common raw/hedge sample through `matched_with_coverage`, which delegates alignment to `align_raw_and_hedge_frames`.

That alignment intentionally carries only configured raw signal columns from the raw-flow frame. `flow_classified_contract_volume` is not configured as a raw signal; it is a denominator/activity field. Therefore the column was absent from the aligned frame even though the frozen development protocol requires it for:

- `early_raw_contract_imbalance` denominator; and
- `early_classified_contract_volume`.

This was a data-column wiring bug, not a descriptor-definition, timing, target, threshold, or endpoint-math issue.

## Repair

The repair changes only `_opening_sample()` in `scripts/gexy_tradeflow_session_state_development.py` so that, after the unchanged 90%-coverage matched sample is built, it attaches exactly `flow_classified_contract_volume` from the raw feature frame by the same exact causal `timestamp` with one-to-one validation.

No nearest-time fill, resampling, alternate window, alternate descriptor, or post-09:40 information is introduced.

Repair commit:

- `f49841dd842abbc74f90e12aefd97ada5088da8c`

A regression test was added that constructs a minimal causal raw/hedge sample and verifies that `flow_classified_contract_volume` survives `_opening_sample()` alongside the configured raw signal.

Regression-test commit:

- `614aba0594534bcc4ddec4b1ee73738bcade1f47`

## Execution rule after repair

Before re-running the development screen:

1. sync the repair commits;
2. re-run the session-state safeguard test file;
3. proceed only if all safeguards pass;
4. then run the same frozen development-screen command once.

If another structural error occurs, stop again before interpreting or changing any research rule.

## Scientific integrity

Because the first execution aborted before any descriptor screen result was produced, this repair does not condition on observed candidate performance. The frozen development protocol remains the controlling specification.
