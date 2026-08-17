# GEXY 0DTE Authority Charter

## Status

Adopted as a core specialization of the GEXY primary north-star mission.

GEXY should aspire to become an exceptionally rigorous authority on zero-days-to-expiration (0DTE) index options, with SPX/SPXW as the primary research domain. Authority must be earned through transparent measurement, prospective validation, calibrated uncertainty, and a permanent audit trail.

This charter does not modify the frozen 2026-08-17 through 2026-08-21 prospective replication. That block must be completed and formally recorded unchanged before new 0DTE research dimensions influence official prospective claims.

## Mission

Build the deepest causally synchronized understanding we can of how 0DTE option activity, positioning, volatility, liquidity, and hedging interact with SPX and ES intraday price formation.

The goal is not merely to calculate gamma levels. GEXY should learn and measure the complete 0DTE market state:

- where option risk is concentrated;
- how that concentration changes intraday;
- which trades appear buyer- or seller-initiated under the frozen inference rules;
- how inferred LP/dealer hedge requirements evolve;
- whether ES futures microstructure confirms, rejects, or leads the inferred hedge pressure;
- how volatility, skew, breadth, rates, and event risk alter the response;
- how these relationships vary by time of day and regime;
- when the evidence is strong enough to forecast and when GEXY should abstain.

## 0DTE research domains

### Contract and surface state

- complete SPXW 0DTE strike map within justified scope;
- calls vs puts;
- distance from spot/forward;
- volume and open interest;
- implied volatility surface;
- skew, smile, and local convexity;
- delta, gamma, vanna, charm and other Greeks where stable and useful;
- strike-localized GEX/GAX and hedge-delta proxies;
- concentration around major strikes and rapidly changing intraday nodes.

### Trade-flow state

- pre-trade NBBO aggressor inference;
- buyer/seller/UNKNOWN classification with UNKNOWN preserved;
- signed contracts and premium;
- classified-volume coverage;
- strike- and option-type-localized flow;
- burst/intensity measures;
- large-trade diagnostics;
- opening, midday, event, and closing flow states.

### Hedge-response state

- inferred opposite-side LP/dealer option exposure proxy;
- `hedge_delta_units` and Greek-weighted hedge-pressure measures;
- expected hedge direction and sensitivity to spot movement;
- changes in hedge requirement as spot, IV, and time-to-expiry move;
- distinction between inferred hedge requirement and observed executed hedges.

### ES / CME MBO confirmation

After the frozen prospective block, add Bookmap/CME ES MBO where permitted:

- queue imbalance;
- add/cancel velocity;
- bid/ask replenishment;
- liquidity depletion;
- sweep intensity;
- aggressive trade imbalance;
- microprice and depth pressure;
- short-horizon ES response.

Anonymous MBO must never be represented as participant identity or direct proof of dealer hedging.

### Volatility and regime context

- VIX complex and volatility term structure where available;
- realized vs implied volatility;
- skew changes;
- event-calendar state;
- time-of-day state;
- trend vs mean-reversion state;
- liquidity and volatility regimes;
- expiry/rebalance/calendar effects.

## Forecasting goal

For multiple horizons, including at least 1, 2, 3, 5 and longer candle horizons, GEXY should estimate:

- direction probability;
- expected magnitude;
- uncertainty interval;
- confidence;
- evidence agreement across independent information families;
- explicit `NO FORECAST / LOW CONFIDENCE` state.

Very high accuracy may be pursued only as a measured conditional property of predeclared high-confidence states. Accuracy must always be reported with coverage, sample size, exact horizon, target definition, and whether the data were untouched prospective observations.

## Authority standard

GEXY may call itself authoritative on 0DTE only to the extent supported by evidence. The system must:

- preserve every official result, including failures;
- distinguish observation from inference;
- distinguish correlation from causation;
- avoid hindsight leakage through strict `available_at` timestamps;
- avoid changing signs, thresholds, windows, horizons, strike scopes, or regimes after seeing prospective results and then labeling the result prospective;
- test drift continuously;
- maintain untouched forward blocks;
- publish internally complete accuracy/coverage/calibration records;
- refuse to forecast when evidence quality is insufficient.

## Long-term deliverables

1. A reproducible 0DTE data warehouse with causal timestamps.
2. A complete SPXW intraday option-state engine.
3. A real-time GEX/GAX/hedge-pressure engine.
4. A Bookmap/CME MBO hedge-response confirmation engine.
5. A 0DTE volatility/skew/regime engine.
6. A multi-horizon calibrated forecasting engine.
7. A historical replay and walk-forward research environment.
8. Repeated untouched prospective validation blocks.
9. A permanent 0DTE research ledger documenting what worked, what failed, and when relationships changed.
10. A Bookmap/visual interface showing the current 0DTE state, predicted hedge pressure, confidence, and forecast path without overstating certainty.

## North-star statement

Become one of the most rigorously measured sources of understanding about SPX/SPXW 0DTE behavior by learning how option flow, exposures, volatility, market-maker hedge requirements, futures microstructure, and broader market state interact in real time—and earn any claim of predictive authority through repeated untouched future evidence.
