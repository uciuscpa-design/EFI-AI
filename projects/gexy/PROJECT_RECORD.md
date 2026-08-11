# GEXY — Project Record

## Project identity
- **Name:** GEXY
- **Repository:** ucius cpa-design/EFI-AI
- **Branch:** `feature/gexy`
- **Status:** Milestone 1 in progress
- **Started:** 2026-08-10

## Objective
Build a real-time SPX options market-structure and hedge-flow prediction engine that estimates how options gamma, volatility sensitivity, time decay, options flow, futures flow, and liquidity may influence near-term SPX movement.

## Primary product
GEXY will provide:
1. Real-time SPX/SPXW options positioning analysis.
2. GEX by strike and across price scenarios.
3. Dealer hedge-pressure estimates.
4. Vanna and Charm contributions.
5. Gamma-flip, call-wall, put-wall and major concentration levels.
6. Adjustable forecast horizons.
7. Predicted future SPX movement displayed as an overlay on candlestick charts.
8. A dedicated forecast/hedge-pressure chart.
9. Prediction cones/ranges rather than only a single point forecast.
10. Historical replay and backtesting.
11. Calibration of the relationship between estimated hedge pressure and realized SPX movement.
12. Confidence, invalidation and regime indicators.

## Initial forecast horizons
- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes
- 60 minutes

These must remain configurable.

## Adjustable chart controls
- Lookback window
- Forecast horizon
- Candle interval
- GEX price range
- Expiration selection (0DTE, 1DTE, 2DTE, all)
- Gamma weighting
- Vanna weighting
- Charm weighting
- Options-flow weighting
- Futures-flow weighting
- Confidence threshold

## Core mathematical model
For a dealer delta estimate D:

`dD ≈ Gamma*dS + Vanna*dSigma + Charm*dt`

Estimated hedge demand is the opposite of the dealer delta change:

`dH ≈ -(Gamma*dS + Vanna*dSigma + Charm*dt)`

GEXY will model the response across a range of hypothetical SPX prices rather than relying only on a single aggregate GEX number.

## Important modeling constraint
Public options data does not reveal the complete dealer book or exact dealer identity. GEXY must therefore distinguish between observed data and inferred dealer positioning. Dealer positioning should be modeled as an estimate/ensemble with confidence, not represented as certain fact.

## Prediction output
The forecast engine should eventually produce:
- Direction probability
- Expected move
- Expected absolute move
- Forecast range/cone
- Hedge-pressure direction
- Hedge-pressure magnitude
- Acceleration probability
- Reversal probability
- Confidence score
- Invalidation level
- Regime classification

## Architecture plan
### Engine layers
- `options_surface`: options contracts, IV, Greeks, OI, volume, trades.
- `positioning`: dealer-position hypotheses and confidence.
- `gex_engine`: gamma exposure by strike and scenario price.
- `hedge_engine`: gamma + vanna + charm to estimated hedge demand.
- `flow_engine`: options flow, ES flow and liquidity confirmation.
- `move_engine`: probabilistic future-move forecast.
- `backtest_engine`: historical replay, scoring and calibration.
- `market_data`: real-time and historical provider adapters.
- `api`: FastAPI endpoints and streaming interfaces.
- `ui`: adjustable chart/window and forecast visualization.

## Validation plan
GEXY must be backtested before treating the forecast as reliable. Required evaluation includes:
- Directional accuracy
- Magnitude error
- Calibration of probabilities
- False-signal rate
- Acceleration detection
- Reversal detection
- Performance by gamma regime
- Performance by 0DTE vs non-0DTE
- Performance by volatility/liquidity regime

## Data requirements
The production design should support:
- SPX and SPXW options
- Strike
- Expiration
- Bid/ask/last
- Implied volatility
- Delta
- Gamma
- Vega
- Theta
- Open interest
- Volume
- Trade direction where inferable
- ES/SPX price and volume
- Market microstructure/liquidity inputs
- Volatility inputs such as VIX and SPX IV surface

## Visualization requirements
The primary chart should support:
- Candlesticks
- Current price
- Historical price window
- Predicted median path
- Upper/lower forecast paths
- Confidence cone
- Gamma walls
- Gamma flip
- Important strike concentrations
- Predicted hedge-pressure acceleration zones
- Forecast horizon markers

A separate forecast chart should display expected SPX change versus time and/or hedge pressure versus price.

## Project record policy
Every significant GEXY decision, formula change, data-source decision, architecture change, test result, calibration result, deployment change, and known limitation should be recorded in this project directory and reflected in Git history.

## Milestone history
### Milestone 0 — Project initialization
Completed:
- Project name selected: GEXY.
- Scope established.
- EFI-AI repository selected.
- Dedicated `feature/gexy` branch created.
- Initial project record created.

### Milestone 1 — Repository architecture and mathematical core
Started: 2026-08-10

Implemented:
- `packages/gexy/models.py` normalized option/exposure contracts.
- `packages/gexy/gex.py` signed GEX by strike and scenario-price calculations.
- `packages/gexy/hedge.py` gamma/vanna/charm hedge-pressure decomposition.
- `packages/gexy/positioning.py` explicit dealer-positioning assumption/ensemble scaffold.
- `packages/gexy/scenario.py` price-scenario GEX/hedge-pressure surface.
- `packages/gexy/forecast.py` transparent probabilistic forecast baseline for calibration.
- Deterministic unit tests under `tests/gexy/`.
- Architecture document under `projects/gexy/ARCHITECTURE.md`.

Important implementation notes:
- Dealer positioning is explicitly modeled as an assumption with a confidence weight rather than an observed fact.
- The initial forecast is a research baseline, not a validated trading signal or price-target model.
- The conversion from hedge-pressure units to SPX points must be learned from historical data rather than assumed universally.

Next:
- Greek adapters and unit conventions.
- Gamma flip/wall detection.
- Flow and liquidity adapters.
- Historical replay/backtesting and calibration.
- FastAPI/streaming endpoints and chart DTOs.
- Candlestick forecast overlay.
