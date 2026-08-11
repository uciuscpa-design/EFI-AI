# GEXY Regime-Conditioned Evaluation

The evaluator groups prediction rows by the market regime available at prediction time and reports the same forecast metrics within each group.

## Group key
`gamma | gamma-flip bucket | volatility bucket | 0DTE`

## Metrics
- directional accuracy
- Brier score
- SPX-point MAE
- mean bias
- sample count

## Important methodology
The current implementation fits a supplied model once on the provided rows and then slices its predictions by regime. This is intended for descriptive conditional analysis. It must not replace the locked chronological out-of-sample evaluation for model selection.

For production research, regime-specific model fitting and thresholds must be selected using training/validation data only, followed by a locked test evaluation.
