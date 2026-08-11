# GEXY Multi-Horizon Experiments

The same model-comparison protocol is run independently for each forecast horizon.

## Target horizons
- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes
- 60 minutes

## Principle
Each horizon must have its own forward labels. A model is not allowed to reuse a label generated for another horizon.

## Comparisons
- GEX
- GEX + Vanna
- GEX + Vanna + Charm
- Full feature set

## Required reporting
For every horizon and model:
- directional accuracy
- Brier score
- SPX-point MAE
- mean bias
- sample count

## Interpretation
Short horizons may be dominated by microstructure/noise, while longer horizons may incorporate more information from volatility, flow and liquidity. Results should therefore be treated as horizon-specific rather than collapsed into a single score.
