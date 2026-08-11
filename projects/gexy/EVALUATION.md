# GEXY Out-of-Sample Evaluation

## Split
Rows remain chronological and are split 60% train, 20% validation, 20% test.

## Current baseline
The current evaluator fits the ridge-style movement model on **training data only** and reports metrics only on the held-out test period. The validation set is intentionally preserved for later hyperparameter selection.

## Reported metrics
- Directional accuracy
- Brier score
- Mean absolute error in SPX points
- Mean bias
- Sample counts

## Required extensions
Future evaluation must add:
- zero-move baseline comparison
- recent-return baseline comparison
- GEX-only model
- GEX + Vanna
- GEX + Vanna + Charm
- full flow/liquidity model
- horizon-by-horizon results
- gamma-regime breakdown
- gamma-flip proximity
- 0DTE vs non-0DTE
- volatility/liquidity regimes
- confidence calibration

## Interpretation rule
No result is considered evidence of a causal dealer-hedging mechanism merely because it predicts future returns. The result establishes predictive association under the model's positioning assumptions. Causal claims require stronger identification and/or external evidence.
