# GEXY Post-Prospective Intelligence Implementation Backlog

## Status

APPROVED implementation backlog for GEXY after the frozen 2026-08-17 through 2026-08-21 prospective SPXW replication is completed and its official result is recorded.

This backlog does not modify, reinterpret, expand, or contaminate the current prospective protocol. No module below may alter the frozen August 17-21 acquisition rules, features, target, horizon, reveal procedure, adjudication, or official result.

## Purpose

Implement the additional intelligence systems recommended for GEXY so the project evolves from a strong options/hedge-flow research engine into a causal, multi-source S&P 500 and 0DTE market-intelligence platform.

The implementation principle is evidence first: every new module must expose what was directly observed, what was inferred, when the information became available, its data-quality state, and whether it added genuine untouched forward predictive value.

## Module 1 — Complex-options strategy classifier

Goal: prevent large or unusual SPX/SPXW prints from being misclassified as simple directional bets when they may be legs of spreads, rolls, butterflies, condors, calendars, volatility trades, hedges, or closing transactions.

Planned capabilities:

- cluster near-simultaneous option prints by timestamp, expiry, strike, size, venue/sequence information where available;
- identify candidate verticals, calendars, diagonals, straddles, strangles, butterflies, condors, ratio structures, rolls, and multi-leg packages;
- distinguish likely outright flow from likely complex/package flow;
- preserve an `UNKNOWN_COMPLEXITY` class when evidence is insufficient;
- compute net package delta, gamma, vega, theta/charm-related exposure proxies rather than interpreting each leg independently;
- record confidence and evidence for every classification;
- never assume a large trade is informed directional flow solely because of premium or size.

## Module 2 — Dynamic dealer-pressure scenario engine

Goal: move beyond static GEX/GAX levels and calculate how inferred hedge pressure changes across nearby future price and time states.

Planned capabilities:

- recompute option Greeks and hedge-pressure proxies over configurable SPX price shocks;
- include time-decay progression throughout the session, especially for 0DTE;
- evaluate nearby strike crossings and local gamma concentration;
- create price-state maps for inferred hedge acceleration/deceleration;
- identify candidate positive-feedback, negative-feedback, pin/magnet, and transition zones without treating them as causal facts until prospectively validated;
- expose scenario grids for multiple horizons;
- preserve the existing definition of `hedge_delta_units` as an inferred LP/dealer hedge proxy, not observed inventory or executed hedges.

## Module 3 — CME/Bookmap iceberg and hidden-liquidity intelligence

Goal: use ES MBO/order-book behavior to detect directly observable replenishment patterns and statistically inferred hidden-liquidity/absorption states.

Planned capabilities:

- deterministic MBO book reconstruction from CME sample data first;
- per-order add/replace/cancel lifecycle tracking where the feed supports it;
- queue depletion and replenishment statistics;
- repeated displayed-size refill detection;
- execution-vs-displayed-liquidity diagnostics;
- absorption and exhaustion features;
- native-iceberg-style evidence where exchange semantics support direct inference;
- separate labels for directly observable exchange behavior versus heuristic `iceberg_like` patterns;
- no participant/dealer identity inference from anonymous order IDs.

## Module 4 — Auction-imbalance intelligence

Goal: model opening and closing auction pressure in SPY and high-weight S&P 500 constituents when timely licensed imbalance feeds are available.

Planned capabilities:

- causal ingestion of official imbalance messages and indicative-price information where licensed;
- constituent-weighted aggregate imbalance measures;
- SPY/ETF auction-pressure measures;
- imbalance acceleration, reversal, persistence, and concentration features;
- opening/closing regime specialist;
- interaction tests with GEXY options pressure, breadth, ES MBO, and volatility;
- strict `available_at` timestamps so no imbalance message influences a forecast before publication.

## Module 5 — Liquidity-vacuum / magnet / pin engine

Goal: combine option-derived strike pressure with actual futures liquidity to distinguish likely pinning/magnet behavior from resistance/support and low-liquidity acceleration states.

Planned capabilities:

- option strike concentration maps;
- dynamic gamma/hedge-pressure scenario maps;
- ES MBO depth, depth slope, queue resilience, replenishment, and cancellation states;
- distance-to-key-strike and distance-to-liquidity-wall features;
- candidate state classes: `MAGNET_PIN`, `RESISTANCE_SUPPORT`, `LIQUIDITY_VACUUM`, `TRANSITION`, `UNKNOWN`;
- probability/confidence rather than deterministic labels;
- prospective tests of whether state classifications improve multi-candle direction and magnitude forecasts.

## Module 6 — Forecast competition / expert ensemble

Goal: make each information family produce an independent forecast, measure its reliability through time, and combine experts only with walk-forward information.

Initial experts:

- SPX/SPXW options and hedge-flow expert;
- complex-options / whale-flow expert;
- ES MBO microstructure expert;
- iceberg/hidden-liquidity expert;
- breadth/constituent expert;
- volatility expert;
- rates/cross-asset expert;
- auction expert;
- price/market-structure expert;
- event/news expert when causally timestamped data is available.

Planned outputs per expert:

- direction probability;
- expected magnitude;
- uncertainty interval;
- quality/confidence state;
- regime tag;
- data freshness;
- recent walk-forward calibration/reliability.

Ensemble requirements:

- no use of future outcomes when setting real-time weights;
- weights derived only from prior information;
- permit expert down-weighting when recent calibration degrades;
- report expert disagreement explicitly;
- support full abstention when disagreement/uncertainty is too high;
- evaluate accuracy together with forecast coverage.

## Module 7 — GEXY Causal Event Recorder

Goal: create a permanent timestamped event graph that records the sequence of observable market events before and after each forecast.

Each event should include at minimum:

- `event_time`;
- `available_at`;
- source/feed;
- event family;
- symbol/instrument;
- raw observable facts;
- inferred interpretation, if any;
- inference confidence;
- data-quality flags;
- model version;
- feature-version hashes where practical;
- associated forecast IDs;
- future outcome links added only after outcomes become observable.

Candidate event families:

- unusual/large SPXW flow;
- candidate complex strategy;
- inferred hedge-pressure change;
- strike/gamma transition;
- ES queue imbalance shift;
- add/cancel burst;
- sweep/aggressive trade burst;
- absorption or iceberg-like replenishment;
- breadth regime change;
- volatility shock;
- auction imbalance update;
- cross-asset regime shift;
- scheduled macro/news event;
- GEXY forecast issuance, revision, abstention, invalidation, and outcome.

The recorder must never backfill an event into an earlier `available_at` time merely because later information makes the event easier to interpret.

## GEXY CONVICTION output layer

After the expert infrastructure is validated, implement a user-facing conviction layer rather than a single opaque score.

Planned display:

- overall GEXY conviction 0-100;
- direction: upside / downside / no forecast;
- multi-horizon direction probabilities;
- expected move magnitude;
- uncertainty interval;
- expert contribution scores;
- expert disagreement score;
- data-quality score;
- regime reliability;
- trigger/transition levels where statistically justified;
- invalidation/condition-change markers where defined prospectively;
- explicit `NO FORECAST` state.

The conviction score must be calibrated prospectively. A displayed value such as 95 cannot be treated as a 95% empirical probability unless calibration data supports that interpretation.

## Whale / unusual-flow integration

Whale and unusual options activity remain evidence families, not labels for informed traders.

Features may include:

- premium and contract-size anomaly scores;
- repeated large-print clustering;
- aggressor-side imbalance;
- strike/expiry concentration;
- IV/skew response;
- Greek-weighted exposure impact;
- candidate sweep behavior;
- candidate complex-package classification;
- whether the flow is opening/closing only where the data genuinely supports that inference.

No `SMART_MONEY` ground-truth label is permitted without a directly supportable definition.

## Dark/off-exchange integration

Where timely, licensed data is available, create a separate off-exchange evidence family for SPY, major ETFs, and important S&P constituents.

Requirements:

- preserve publication/reporting delay in `available_at`;
- never use delayed prints to predict moves that occurred before the print was observable;
- distinguish trade size/price/location facts from trader intent;
- test incremental value only after causal timestamp alignment;
- include abnormal off-exchange volume, large-print clustering, repeated price-level activity, and interaction with options/MBO/breadth where supported.

## Implementation order

The approved post-prospective sequence is:

1. Complete and formally record the 2026-08-17 through 2026-08-21 prospective result.
2. CME sample MBO parser and deterministic order-book reconstruction.
3. MBO feature engine including queue, cancel, replenishment, sweep, absorption, and iceberg diagnostics.
4. Bookmap CME ES adapter if technically and contractually permitted.
5. Complex-options strategy classifier.
6. Dynamic dealer-pressure scenario engine.
7. Liquidity-vacuum / magnet / pin engine.
8. Causal Event Recorder core schema and logging pipeline.
9. S&P constituent/breadth engine.
10. Volatility-complex engine.
11. Rates/cross-asset engine.
12. Auction-imbalance engine where licensed timely data is available.
13. Whale/unusual-flow specialist integrated with complex-strategy classification.
14. Dark/off-exchange evidence family where timely licensed data is available.
15. Independent expert forecast APIs.
16. Walk-forward expert competition/reliability layer.
17. Calibrated ensemble and abstention engine.
18. GEXY CONVICTION presentation layer.
19. Freeze a new untouched prospective protocol before making official multi-source predictive claims.
20. Repeated untouched prospective blocks, drift monitoring, and only then production-deployment consideration.

## Non-negotiable scientific rules

- Current August 17-21 prospective experiment remains unchanged.
- Every new input requires a causal `available_at` timestamp.
- Observed facts and inferred interpretations must be stored separately.
- No future label leakage into feature generation, expert weighting, regime selection, or confidence scoring.
- No post-hoc threshold or sign optimization may be described as prospective.
- Accuracy must always be paired with coverage and sample size.
- High-confidence accuracy is valid only on the predeclared subset selected without seeing future outcomes.
- GEXY may abstain; it is never required to predict every candle.
- Preserve failures, weak periods, drift, and abstentions in the permanent audit trail.
- Extraordinary performance claims require repeated untouched forward evidence.

## Definition of success

This backlog succeeds when GEXY can explain, at forecast time, not only what it predicts but which independent evidence families support the prediction, which disagree, how fresh/complete the data is, how well each expert has been calibrated on prior unseen data, and when the correct action is to issue no forecast.
