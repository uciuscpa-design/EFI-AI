# GEXY S&P 500 Total-Market Intelligence Roadmap

## Project status — PRIMARY GEXY NORTH-STAR MISSION

Adopted on 2026-08-17 as the primary long-term goal for GEXY.

This document is the authoritative roadmap for what GEXY becomes after the current frozen prospective SPXW replication is completed and formally recorded. The existing 2026-08-17 through 2026-08-21 prospective protocol remains the immediate unfinished prerequisite and must not be changed, expanded, reinterpreted, or contaminated by any of the new total-market ideas below.

The project sequence is therefore:

1. Finish the current frozen prospective replication exactly as predeclared.
2. Record its official result before any post-hoc analysis.
3. Begin implementation of this total-market intelligence roadmap as GEXY's primary development program.
4. Preserve the same scientific discipline for every new information family and every future predictive claim.

This roadmap and the previously recorded Bookmap/CME MBO integration roadmap are complementary. CME/Bookmap MBO becomes the first major new information family after the prospective block is complete.

## Objective

Evolve GEXY from an SPXW option-flow and hedge-pressure research engine into a broad S&P 500 market-intelligence system that fuses independently sourced information streams into calibrated multi-horizon forecasts.

The aspiration is maximum achievable predictive accuracy and reliability, not a guaranteed fixed hit rate. A blanket promise of 95%+ accuracy five or more candles ahead across all regimes is not scientifically credible. The system should instead maximize validated out-of-sample accuracy, probability calibration, magnitude accuracy, and selective high-confidence precision while abstaining when evidence is weak or contradictory.

## Core prediction outputs

For configurable horizons (for example 1, 2, 3, 5, 8, 13, 21 candles), produce:

- probability of upward vs downward move;
- expected move magnitude;
- prediction interval / uncertainty band;
- confidence score;
- regime classification;
- evidence agreement score across independent data families;
- explicit `NO FORECAST / LOW CONFIDENCE` state when uncertainty is too high.

Accuracy must always be reported together with coverage. A 95% hit rate on only a small, predeclared high-confidence subset is fundamentally different from 95% accuracy on every candle.

## Information families

### 1. SPX/SPXW options microstructure
- OPRA trades and pre-trade consolidated BBO;
- 0DTE and selected near-dated expirations;
- strike/expiry concentration;
- GEX, GAX and delta/gamma exposure proxies;
- inferred hedge delta units;
- option trade aggressor imbalance;
- IV surface/skew/term-structure changes;
- put/call and strike-localized flow;
- open-interest positioning where available.

### 2. CME ES futures MBO / order-book microstructure
- per-order add/replace/cancel events where licensed;
- queue imbalance;
- depth-weighted pressure;
- add/cancel velocity;
- queue depletion and replenishment;
- aggressive trade imbalance;
- sweep intensity;
- microprice;
- liquidity gaps and depth slope;
- large-order and iceberg-related diagnostics based only on observable events;
- short-horizon realized ES response.

Use CME sample MBO first, then Bookmap CME MBO where technically and contractually permitted.

### 3. Index and constituent breadth
- SPX constituent advances/declines;
- percentage above/below VWAP and moving anchors;
- sector breadth;
- equal-weight vs cap-weight divergence;
- mega-cap contribution concentration;
- market breadth thrust/decay;
- intraday dispersion and correlation.

### 4. Volatility complex
- VIX and related volatility indices where licensed/available;
- VIX futures term structure;
- implied vs realized volatility;
- skew and convexity measures;
- volatility-of-volatility;
- intraday vol shock detection.

### 5. Rates and macro cross-assets
- Treasury yields and futures;
- yield-curve changes;
- USD / DXY proxies;
- crude oil and gold where informative;
- credit-spread proxies;
- major equity-index futures relationships;
- macro release calendar and surprise information when available causally.

### 6. ETF and equity order flow
- SPY/QQQ and sector ETF price/volume/order-flow inputs;
- constituent-level abnormal volume and price pressure;
- dark/off-exchange statistics only where timely and legally available;
- cross-venue confirmation without participant-identity claims.

### 7. Market structure and time-state
- opening/closing auction context;
- overnight gap and globex structure;
- VWAP, prior-day levels and volume profile;
- time-of-day effects;
- expiry, rebalance and index-event calendars;
- scheduled macro/Fed events;
- realized liquidity and volatility regime.

### 8. News / text / event intelligence
Use only timestamped information available before each forecast. Potential sources:
- scheduled economic releases;
- central-bank communications;
- major index-constituent news;
- earnings surprises for high-weight components;
- geopolitical or macro headlines;
- sentiment/event embeddings.

Text-derived signals must be isolated and tested incrementally so hindsight leakage cannot enter the model.

## Modeling architecture

### Layer A — causal synchronization
Every feature must have a strict `available_at` timestamp. No input may enter a forecast before it was actually observable.

### Layer B — specialized experts
Train separate experts for independent information families, such as:
- options/hedge-flow expert;
- MBO microstructure expert;
- volatility expert;
- breadth/constituent expert;
- cross-asset/macroeconomic expert;
- price/market-structure expert;
- event/news expert.

### Layer C — regime engine
Classify market state using features known at forecast time. Candidate regimes may include trend, mean-reverting, high-volatility, low-liquidity, event-driven, opening, midday, closing and expiry/rebalance states. Regime definitions must be frozen before prospective evaluation if used for official claims.

### Layer D — calibrated ensemble / gating model
Fuse expert probabilities and magnitude forecasts. The gating model should learn when each expert is historically reliable while remaining strictly walk-forward.

### Layer E — abstention / selective prediction
Allow GEXY to decline a forecast when:
- experts strongly disagree;
- data quality is inadequate;
- the state is far outside training distribution;
- calibration suggests low reliability;
- a feed is stale or incomplete.

This selective-prediction layer is the scientifically valid route to pursuing very high conditional hit rates.

## Evaluation standards

Do not optimize a single headline accuracy number. Track:
- directional accuracy;
- high-confidence directional accuracy;
- forecast coverage at each confidence threshold;
- Brier score / log loss;
- probability calibration curves;
- expected calibration error;
- magnitude MAE/RMSE;
- sign-and-magnitude joint score;
- maximum adverse excursion / favorable excursion after forecasts;
- performance by horizon;
- performance by time of day;
- performance by regime;
- walk-forward and untouched prospective performance;
- degradation / drift over time.

Any 95%+ claim must specify exact horizon, target definition, confidence threshold, coverage, sample size, date range, fees/slippage assumptions where trading is involved, and whether the test was untouched prospective data.

## Scientific safeguards

- No random train/test split for time series where leakage can occur.
- Use purged/embargoed temporal validation where appropriate.
- Maintain untouched forward blocks.
- Never tune feature signs, thresholds, horizons or regimes after seeing prospective outcomes and call them prospective.
- Record every experiment, protocol and official result before post-hoc diagnostics.
- Separate research correlation from causal claims.
- Never infer dealer/customer identity from anonymous futures MBO.
- Never deploy capital solely because a historical backtest exceeds a target accuracy.

## Development sequence

1. Finish the frozen 2026-08-17 through 2026-08-21 prospective GEXY replication unchanged.
2. Build CME sample MBO replay/reconstruction laboratory.
3. Connect Bookmap CME ES MBO if licensing permits.
4. Add causal MBO feature engine and incremental-value tests.
5. Add S&P breadth / constituent-state engine.
6. Add volatility-complex features.
7. Add rates/cross-asset regime inputs.
8. Add event/news intelligence with strict timestamps.
9. Build multi-expert calibrated ensemble.
10. Add abstention/selective-prediction layer.
11. Freeze a new forward protocol for multi-source GEXY.
12. Run repeated prospective blocks before considering production deployment.

## North-star goal

Build the most rigorously measured S&P 500 forecasting system we can: broad information coverage, causal timestamps, multi-source agreement, explicit uncertainty, selective high-confidence forecasts, continuous drift detection, and a permanent audit trail.

The goal is not to force every candle into a prediction. The goal is to know when the evidence is unusually strong, quantify that strength honestly, and prove it repeatedly on untouched future data.
