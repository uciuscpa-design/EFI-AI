# GEXY Architecture — Milestone 1

## Pipeline

`market_data -> normalized_options -> positioning -> gex_engine -> hedge_engine -> move_engine -> api/ui`

## Core contracts

### OptionContract
Normalized per-contract inputs: strike, expiration, type, OI, Greeks, multiplier, dealer-position hypothesis and confidence.

### GEXSnapshot
Aggregate and per-strike signed gamma exposure for a supplied spot price.

### HedgePressure
Estimated dealer delta change and opposing underlying hedge demand, decomposed into gamma, vanna and charm components.

## Modeling rules

1. Observed market facts and inferred dealer positioning are separate concepts.
2. Dealer sign is configurable; no single assumption is treated as ground truth.
3. Confidence scales inferred exposure and is retained in outputs.
4. Scenario calculations operate over a price grid, not only the current spot.
5. The future-move model will not be activated as a trading signal until historical validation is complete.

## Next implementation slices

- Add Black-Scholes/market-data Greek adapters with explicit units.
- Add dealer-position hypothesis ensemble.
- Add gamma flip and wall detection.
- Add scenario hedge-pressure surface.
- Add probabilistic move engine.
- Add historical replay/backtest schema.
- Add FastAPI endpoints and streaming interface.
- Add chart-facing forecast DTOs.
