# GEXY Model Comparison

## Goal
Measure the incremental predictive value of the principal GEXY components without changing the held-out test period.

## Nested variants
1. `gex` — GEX only
2. `gex_vanna` — GEX + Vanna
3. `gex_vanna_charm` — GEX + Vanna + Charm
4. `full` — all current dynamic features

Every variant uses the same chronological train/validation/test boundaries.

## Metrics
- Directional accuracy
- Brier score
- MAE in SPX points
- Mean bias

## Interpretation
A component is useful only if its addition improves out-of-sample performance consistently enough to survive comparison across horizons and market regimes. A single favorable test period is not sufficient evidence.

## Next extensions
- Include zero-move and recent-return baselines in the same report.
- Run independently for 1m, 5m, 15m, 30m and 60m horizons.
- Add gamma-regime and gamma-flip-distance buckets.
- Add 0DTE/non-0DTE comparisons.
- Add volatility/liquidity regime slices.
- Use validation data for alpha/model selection before the final locked test.
