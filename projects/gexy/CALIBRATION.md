# GEXY Calibration Protocol

## Purpose
Measure whether GEXY's estimated hedge-pressure state contains out-of-sample information about future SPX movement.

## Horizons
1m, 5m, 15m, 30m, 60m.

## Required timestamp inputs
Each feature snapshot must be timestamped before the forecast horizon begins. Future information must never enter the feature vector.

## Labels
For snapshot price S(t) and future price S(t+h):

`move_h = S(t+h) - S(t)`

Direction is `move_h > 0`. Absolute movement is `abs(move_h)`.

## Metrics
- Directional accuracy
- Mean absolute error of predicted points
- Mean bias
- Brier score for direction probability
- Forecast-range coverage when prediction cones are added
- Acceleration/reversal precision and recall when those labels are introduced

## Required splits
- Chronological train/validation/test splits
- No random shuffling across time
- Separate evaluation by 0DTE vs non-0DTE
- Separate evaluation by positive/negative/near-zero GEX regime
- Separate evaluation by volatility and liquidity regime

## Leakage controls
- Do not use future OI or future Greeks in a snapshot.
- Do not calculate trade direction using information after the snapshot timestamp.
- Do not fit scaling/calibration parameters on the test period.
- Preserve provider timestamps and source identifiers.

## Baseline requirement
Compare GEXY against simple baselines such as:
- zero-move forecast
- recent-return momentum
- realized-volatility range
- direction-at-50% baseline

A GEXY feature is considered useful only when it improves out-of-sample metrics beyond relevant baselines and remains stable across time/regimes.

## Interpretation
No metric alone proves causal dealer hedging. Results measure predictive association under the specified positioning assumptions and data limitations.
