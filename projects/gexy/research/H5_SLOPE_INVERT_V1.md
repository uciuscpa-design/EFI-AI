# GEXY-H5-SLOPE-INVERT-v1

Status: **preregistered research hypothesis — shadow evaluation only**  
Frozen: **2026-08-14**  
Production predictor changed: **no**  
Execution enabled: **no**

## Hypothesis

Within the `negative_gamma_acceleration` regime at a 5-minute forecast horizon, the sign of `local_gex_slope` may be more useful when interpreted opposite to the current first-pass negative-gamma mapping.

Frozen rule:

- `local_gex_slope > 0` -> predict **down**
- `local_gex_slope < 0` -> predict **up**
- zero or missing slope -> no score for this hypothesis

No other feature, threshold, time-of-day filter, wall rule, confidence threshold, or horizon may be added to this version after seeing future results. Any modification requires a new versioned hypothesis.

## Selection-session evidence — 2026-08-14

This evidence selected the hypothesis and is **not independent validation**.

- Full 5-minute sample: inverted slope accuracy **57.67%** vs always-down **55.03%**; lift **+2.65 percentage points**.
- Early chronological 70%: inverted slope **56.82%** vs always-down **59.85%**; lift **-3.03 percentage points**.
- Late chronological 30%: inverted slope **59.65%** vs always-down **43.86%**; lift **+15.79 percentage points**.
- Current predictor in the late 30%: **38.60%**.

The instability between the early and late windows suggests a possible time/regime interaction rather than a stable universal inversion. The late-window result must therefore be treated as exploratory.

## Independent evaluation protocol

Evaluate this exact frozen rule on subsequent separately captured market sessions without changing the rule.

For each session record:

1. resolved 5-minute sample count;
2. realized up/down/flat class balance;
3. frozen-rule directional accuracy;
4. always-down directional accuracy;
5. lift versus always-down;
6. current-predictor directional accuracy;
7. feature/data coverage and regime coverage.

A session is considered informative when at least **50 resolved 5-minute forecasts** can be matched exactly to their captured surface observation.

## Promotion gate

Do **not** change the production predictor based on the 2026-08-14 session.

The hypothesis may advance only to a separate **shadow-model experiment** after:

- at least **two subsequent independent informative sessions** have positive lift versus their own always-down baseline; and
- the aggregate of those independent sessions also has positive lift versus always-down.

Even if those conditions pass, this does not authorize trading or execution. Any production change requires its own review, tests, backtest/forward-test evidence, and explicit safety gate.

## Data integrity rules

- Join surface observations to predictions by the exact prediction timestamp; do not use future features.
- Preserve missing provider data as missing.
- Do not fabricate IV, Greeks, dealer positioning, or gamma-flip values.
- Keep multiple horizons sharing one observation identifiable as correlated measurements.
- Report class imbalance and the constant-direction baseline with every accuracy result.

## Next planned independent observation

The Windows `GEXY Session Collector` task was verified `Ready` on 2026-08-14. Its next scheduled run is **2026-08-17 06:20 PDT**. This schedule is for data collection only; it does not enable execution.
