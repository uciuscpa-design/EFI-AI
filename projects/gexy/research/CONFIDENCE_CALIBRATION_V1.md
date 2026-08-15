# GEXY-CONFIDENCE-CAL-v1

Status: **preregistered research reliability model — shadow evaluation only**  
Selection session: **2026-08-14**  
Production confidence changed: **no**  
Production direction changed: **no**  
Execution enabled: **no**

## Problem being corrected

The first-pass live predictor reports `confidence=0.95` for every resolved shadow forecast in the 2026-08-14 captured sample.

Diagnostics established that this is mechanical saturation rather than calibration:

- the 0.95 clamp is reached once the internal raw score exceeds about `2.996`;
- the observed raw score ranges from roughly `16,182` to `5,050,625`;
- `abs(local_gex_slope)` contributes more than 99.9999% of the structure term at the median, overwhelming the hedge-acceleration term because the inputs are on incompatible scales;
- raw-score accuracy is non-monotonic across quartiles;
- raw-score quartiles are strongly confounded with predicted direction, while the current up/down branches have very different realized reliability.

Therefore v1 explicitly rejects a simple rescaling of the current raw score.

## Meaning of the research output

`GEXY-CONFIDENCE-CAL-v1` estimates:

`P(current predicted direction is correct)`

It does **not** choose or invert the predicted direction. A probability below 0.5 is permitted and means the current forecast branch was historically unreliable in the frozen selection sample.

## Frozen v1 inputs

Only these inputs are used:

1. forecast horizon: `5`, `15`, `30`, or `60` minutes;
2. current predicted direction: `up` or `down`;
3. regime must be exactly `negative_gamma_acceleration`.

No raw-confidence score, time-of-day filter, wall distance, GEX magnitude threshold, momentum feature, or other feature is used in v1.

## Frozen fitting rule

Fit only resolved forecasts from **2026-08-14** that satisfy the supported horizon, direction, and regime requirements.

For each `(horizon, predicted_direction)` cell:

- `n` = resolved forecasts;
- `k` = directional hits;
- require at least 20 rows;
- calibrated reliability = Jeffreys posterior mean:

`(k + 0.5) / (n + 1)`

The horizon-only Jeffreys posterior is also frozen as a stronger baseline than constant 0.5.

Unsupported or undersized cells are unscored rather than assigned an invented probability.

## Independent evaluation

Every session after 2026-08-14 is independent of the selection fit.

For each future session report:

- scored row count;
- observed directional accuracy;
- mean predicted reliability;
- calibration gap;
- Brier score;
- log loss;
- Brier score for the frozen horizon-only baseline;
- Brier score for constant 0.5;
- per-cell calibration diagnostics.

A future session is informative when at least **50** supported resolved forecasts are scored.

A session is a positive calibration result only when the v1 Brier score is better than **both**:

1. the frozen horizon-only selection baseline; and
2. constant 0.5,

on exactly the same future rows.

## Promotion gate

Do not replace production confidence using the selection session.

The model may advance only to review of a separate shadow reliability layer after:

- at least **two subsequent independent informative sessions** are positive calibration results; and
- the aggregate across all informative independent sessions also beats both Brier baselines.

A passing gate still does not authorize production confidence replacement, direction changes, order submission, or execution.

## Integrity rules

- The 2026-08-14 selection fit is diagnostic/training evidence, not validation.
- All informative future sessions remain in the aggregate, including bad sessions.
- No parameter may be retuned after future results without creating a new versioned model.
- New market regimes require separate evidence; negative-gamma calibration must not be silently applied to positive gamma.
- Existing provider-data provenance rules remain unchanged.
