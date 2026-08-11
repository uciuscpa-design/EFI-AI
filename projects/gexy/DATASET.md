# GEXY Research Dataset

## Purpose
Create leakage-safe rows suitable for statistical analysis and future model training.

## Row structure
Each row contains point-in-time features plus a forward outcome label:

`timestamp, SPX, ΔSPX, ΔIV, GEX, ΔGEX, Vanna, Charm, hedge demand, positioning confidence, forward label`

## Horizons
The assembler is parameterized for 1m, 5m, 15m, 30m and 60m. Separate datasets or horizon columns may be produced later.

## Join rule
Feature rows join to labels using the exact source timestamp. The label is generated from the first eligible future market snapshot at or after the requested horizon.

## Leakage controls
- Features are never shifted forward.
- Future prices are used only for labels.
- No future option-chain fields are included in a feature row.
- Missing timestamps do not trigger synthetic future prices.

## Next research layer
The assembled rows will feed chronological train/validation/test splits and baseline/model comparisons. Model fitting must occur only on the training period; calibration parameters must not be estimated from the test period.
