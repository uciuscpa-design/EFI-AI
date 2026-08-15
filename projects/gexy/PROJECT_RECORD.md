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
- `packages/gexy/levels.py` gamma flip/call-wall/put-wall level detection.
- `packages/gexy/adapters/alpaca.py` provider adapter contract/capability boundary.
- `packages/gexy/calibration.py` leakage-safe labels and forecast scoring metrics.
- `packages/gexy/replay.py` chronological forward-label replay engine.
- `packages/gexy/backtest.py` chronological train/validation/test split utility.
- Deterministic unit tests under `tests/gexy/`.
- Architecture document under `projects/gexy/ARCHITECTURE.md`.
- Calibration protocol under `projects/gexy/CALIBRATION.md`.

Important implementation notes:
- Dealer positioning is explicitly modeled as an assumption with a confidence weight rather than an observed fact.
- The initial forecast is a research baseline, not a validated trading signal or price-target model.
- The conversion from hedge-pressure units to SPX points must be learned from historical data rather than assumed universally.
- Calibration must use chronological, leakage-safe evaluation and compare against simple baselines.
- Replay targets are deliberately separated from source-time features to reduce temporal leakage.

### Milestone 1 calibration phase
Started: 2026-08-11

Completed:
- Forward-move label structure for configurable horizons.
- Directional accuracy, MAE, bias and Brier-score metrics.
- Calibration protocol specifying chronological train/validation/test splits.
- Explicit leakage controls.
- Chronological replay target generation.
- Deterministic temporal backtest splitting.

Tracking:
- GitHub Issue #6: `GEXY: historical options data and calibration pipeline`.

### Milestone 1 live-shadow calibration checkpoint — 2026-08-14

Completed:
- Verified real SPX options ingestion through Alpaca while preserving quote/trade/open-interest timestamp provenance and missing provider IV/Greeks as missing.
- Built a Windows session collector with raw observations, production prediction journal, full 1–60 minute shadow grid, leakage-safe label resolution, immutable session snapshots, cadence diagnostics and strict readiness checks.
- Matched **9,140 / 9,140** resolved shadow forecasts to source-time live feature observations for research diagnostics.
- Confirmed the current first-pass shadow predictor is not promotion-ready: overall direction accuracy was about **52.17%** versus about **73.84%** for the best constant-direction (`always down`) baseline in the resolved sample.
- Isolated the predicted-up branch as the dominant wrong-sign failure mode and confirmed that blindly flipping all up calls merely reproduces the always-down baseline rather than establishing alpha.
- Added live feature ablation for local GEX slope, hedge acceleration, wall distances, spot momentum and time-of-day with exact timestamp joins and Windows UTF-8/UTF-16 log normalization.
- Preregistered `GEXY-H5-SLOPE-INVERT-v1` as a 5-minute negative-gamma shadow hypothesis after an exploratory late-session result; production direction logic was not changed.
- Added an independent-session H5 evaluator that excludes the 2026-08-14 selection session and requires at least two later informative sessions with positive lift plus positive aggregate lift before shadow-experiment review.
- Audited the original confidence formula and confirmed mechanical saturation at 0.95 because local-GEX slope numerically dominates the structure term by orders of magnitude. Raw-score accuracy was non-monotonic and strongly confounded with predicted direction, so simple rescaling was rejected.
- Preregistered `GEXY-CONFIDENCE-CAL-v1`, a research-only estimate of `P(current predicted direction is correct)` conditioned on production horizon, current predicted direction and the observed negative-gamma regime.
- Frozen `GEXY-CONFIDENCE-CAL-v1` with Jeffreys/Beta smoothing on the 2026-08-14 selection sample. The frozen artifact is `projects/gexy/research/CONFIDENCE_CALIBRATION_V1_MODEL.json`.
- Frozen calibration fingerprint: `24b38617e061c18a864c3c871c863504e10a3c146eb81d3c7f4cded93b81cab0`.
- Added a hard fingerprint drift guard: any change to the frozen selection fit returns `selection_model_drift` and blocks future-session scoring instead of silently refitting v1.
- Full Windows test suite after the frozen-model drift guard: **205 passed**, with one unrelated Starlette/httpx deprecation warning.
- Real integrity rerun confirmed expected fingerprint equals actual fingerprint and calibration status is `awaiting_independent_sessions`.

Frozen confidence-calibration selection values (research/training only; not independent validation):
- 5m down `P(correct)=0.4750`; 5m up `0.3571`.
- 15m down `0.6720`; 15m up `0.4091`.
- 30m down `0.7771`; 30m up `0.3015`.
- 60m down `0.8790`; 60m up `0.0809`.

Safety and interpretation:
- The 2026-08-14 H5 and confidence results are selection/training evidence, not independent validation.
- Production confidence remains unchanged.
- Production direction logic remains unchanged.
- Execution remains disabled.
- Missing IV, Greeks, gamma-flip inputs or dealer positioning must never be fabricated.
- A research gate passing does not itself authorize production changes or trading.

### Milestone 1 point-in-time SPX/ES infrastructure checkpoint — 2026-08-14

Completed:
- Audited the live SPX reference semantics and confirmed GEXY's current `spot` is inferred from same-strike call/put option midpoint parity rather than a direct SPX cash tick.
- Added `ForwardSpotEstimate` and exact selected parity-pair quote timestamp provenance. Acquisition time is now explicitly distinct from the source event times used to construct the inferred SPX value.
- Frozen the safe SPX synchronization anchor as the **later** quote timestamp of the exact call/put pair required by the selected median parity estimate.
- Added provider-neutral `MarketObservation` and SPX/reference synchronization infrastructure with a frozen 5-second maximum reference lag, statuses for matched/stale/missing rows, and strict no-future matching.
- Added nanosecond event-order support. Provider raw nanosecond timestamps remain the source of truth even when Python's human-readable `datetime` projection collapses multiple events into one microsecond.
- Added a regression test proving a reference event only **1 nanosecond after** the SPX anchor is rejected as future data.
- Added append-only synchronization journal support and coverage/integrity diagnostics for matched, stale, missing, scoreable fraction, lag mean/max/p95, lookahead violations, provenance flags and raw timestamp consistency.
- Added an independent journal-integrity test proving a sub-microsecond future reference is detected even when its ISO datetime text is identical to the SPX anchor.
- Ran a real after-hours Alpaca provenance check. The selected parity pair source timestamps were preserved separately from acquisition time; because the SPX cash session was closed, `scoreable_journaling_allowed=false` and **zero** production, fine-shadow or GAX forecasts were written.
- Selected **Databento** as the preferred first real ES research source, with Massive retained as a fallback. The research selection is documented in `projects/gexy/research/ES_PROVIDER_SELECTION_V1.md`.
- Frozen the first Databento research subscription shape as CME Globex `GLBX.MDP3`, `trades`, continuous selector `ES.v.0`, while requiring the actual raw futures contract symbol and instrument ID to be preserved through point-in-time symbol mapping.
- Added `packages/gexy/databento_es.py`, which normalizes fixed-point trade prices, retains raw `ts_event_ns` and `ts_recv_ns`, preserves raw contract identity, rejects future/mismatched mappings, and converts valid records into provider-neutral `MarketObservation` objects without losing nanosecond order.
- Added `packages/gexy/databento_preflight.py`, a credential-safe readiness check that never prints a key and performs no network request.
- Added the dedicated research workflow `.github/workflows/gexy-databento-preflight.yml`.
- Windows preflight status: `not_configured`; `DATABENTO_API_KEY` is absent, the Databento Python client is not installed, no network request was attempted, and execution/production features remain disabled.
- Full Windows test suite after nanosecond hardening and Databento readiness scaffolding: **232 passed**, with one unrelated Starlette/httpx deprecation warning.

Point-in-time safety rules now enforced:
- A synthetic SPX value is not considered known until all quotes required to construct it have occurred.
- Reference-market observations must satisfy exact event time `<=` the SPX anchor; future nearest-neighbor matching and future interpolation are prohibited.
- Stale or missing reference rows remain unscoreable rather than being silently filled.
- Raw provider nanosecond timestamps are preserved when available; microsecond display timestamps cannot override finer event ordering.
- SPY or another equity proxy must never be stored or described as ES futures.
- Continuous futures symbology is only a selector; persisted data must retain the actual mapped tradable contract identity.
- Synchronized ES data, when available, remains a coverage/integrity input only until a separately versioned ES-derived hypothesis passes chronological validation.
- Production direction, production confidence and execution remain unchanged.

Next:
- Collect the next independent market session with the existing Windows session collector.
- Evaluate the exact frozen H5 slope-inversion hypothesis without retuning.
- Evaluate the exact frozen confidence-calibration model using Brier score against both its frozen horizon-only baseline and constant 0.5.
- Require multiple independent sessions before any shadow-model promotion decision.
- Provision a Databento account/API key externally, set `DATABENTO_API_KEY` locally without committing it, install the Databento Python client, and run a read-only connectivity/symbol-mapping check.
- Once Databento connectivity succeeds, collect SPX/ES synchronization rows for coverage/integrity only and require zero lookahead violations before defining any ES-derived predictive feature.
- Continue historical options/market-data ingestion.
- Add flow/liquidity features only through versioned research hypotheses with leakage-safe validation.
- Continue toward FastAPI/streaming endpoints and chart DTOs after signal/calibration integrity is established.
- Build the candlestick forecast overlay after the research outputs have stable semantics.
