# GEXY Whale / Unusual-Options / Iceberg / Off-Exchange Intelligence

## Status

Official supporting research charter for the GEXY S&P 500 Total-Market Intelligence roadmap. This work is deferred until the frozen 2026-08-17 through 2026-08-21 prospective replication is completed and formally recorded.

## Objective

Add specialized detection and causal testing for unusually large or informative market activity without assuming that size, venue, or hidden-liquidity behavior automatically implies informed trading. Each signal family must be measured independently, timestamped by when it was actually observable, and validated prospectively before it can influence high-confidence GEXY forecasts.

## 1. Whale / large-options-flow intelligence

Track unusually large SPX/SPXW and selected cross-market option activity using features such as:

- premium notional and contract size relative to strike/expiry norms;
- size relative to displayed liquidity and recent volume;
- repeated large trades at related strikes or expirations;
- sweep-like multi-venue executions when observable;
- same-direction clusters over short causal windows;
- strike concentration around spot, expected-move boundaries, major gamma levels, and event levels;
- trade-side inference using the frozen pre-trade NBBO method where applicable;
- delta-, gamma-, vega-, and premium-weighted flow;
- opening vs closing intent only when data supports an inference; otherwise mark unknown;
- subsequent inferred hedge demand and realized SPX/ES response.

Large size is not synonymous with an informed participant. GEXY should use terms such as `large_flow`, `unusual_flow`, or `whale_like_activity` as statistical classifications, not identity claims.

## 2. Unusual-options-activity engine

Build anomaly scores relative to causal historical baselines for:

- volume vs expected intraday volume;
- trade size vs local historical distribution;
- premium vs local historical distribution;
- call/put imbalance;
- aggressor-side imbalance;
- strike/expiry concentration;
- IV/skew changes associated with the flow;
- repeated prints or bursts;
- short-dated and 0DTE concentration;
- flow that is unusual conditional on time-of-day, volatility regime, and scheduled events.

The engine should distinguish `unusual` from `predictive`. An anomaly only becomes a forecasting input after incremental walk-forward and untouched-forward testing.

## 3. Iceberg / hidden-liquidity intelligence

Using CME ES MBO / Bookmap data where licensed and technically available, estimate hidden-liquidity behavior from observable order-book events, including:

- repeated replenishment at the same price after executions;
- displayed size that refills unusually quickly;
- execution volume materially exceeding contemporaneously displayed size;
- persistent queue presence despite repeated depletion;
- add/cancel/replace sequences consistent with reserve-like behavior;
- absorption and exhaustion measures;
- bid-side vs ask-side replenishment asymmetry;
- interaction between iceberg-like behavior and subsequent microprice / ES price movement.

Do not claim a hidden reserve order exists unless the feed explicitly identifies one. Otherwise label results `iceberg_like`, `replenishment`, `absorption`, or similar observable/inferred diagnostics.

## 4. Dark-pool / off-exchange intelligence

Where timely, licensed data is available, track off-exchange or alternative-venue activity for SPY, major S&P 500 constituents, and relevant ETFs. Candidate features include:

- off-exchange volume share;
- unusually large prints relative to the instrument's normal distribution;
- repeated prints near the same price level;
- price-level persistence after large prints;
- constituent and ETF clustering;
- timing relative to SPX option-flow shocks, ES MBO changes, and subsequent index movement;
- delayed-reporting awareness and exact `available_at` timestamps.

Dark/off-exchange prints must never be treated as real-time predictive information before they were actually disseminated. GEXY must not infer buyer/seller identity or institutional intent unless the source explicitly provides it.

## 5. Cross-signal fusion

Test whether these families provide incremental information when combined with existing GEXY experts. Example causal sequence:

`unusual SPXW flow -> inferred hedge pressure -> ES MBO replenishment / depletion -> breadth confirmation -> subsequent SPX movement`

Other candidate interactions:

- whale-like call buying + ask depletion + strengthening breadth;
- whale-like put buying + bid depletion + rising implied volatility;
- large option flow near a major gamma level + iceberg-like ES absorption;
- off-exchange constituent clustering + option-flow and sector-breadth agreement.

These are hypotheses to test, not assumed trading rules.

## 6. Scoring and outputs

Potential independent scores:

- `whale_flow_score`
- `unusual_options_score`
- `iceberg_like_bid_score`
- `iceberg_like_ask_score`
- `absorption_score`
- `off_exchange_anomaly_score`
- `cross_signal_agreement_score`

Each score must include data quality, timestamp freshness, confidence, historical calibration, and whether it is observed or inferred.

## 7. Scientific safeguards

- Preserve strict `available_at` causality.
- No participant-identity claims from anonymous market data.
- No assumption that large trades are directional bets; spreads, hedges, rolls, overwrites, closing trades, and multi-leg structures can produce large prints.
- No assumption that off-exchange activity is bullish or bearish without evidence.
- No assumption that iceberg-like replenishment is dealer activity.
- Test each family alone before allowing the ensemble to exploit interactions.
- Freeze thresholds/features before any official prospective claim.
- Report accuracy together with coverage, horizon, sample size, and regime.

## Development order

1. Finish and record the frozen Aug. 17-21 prospective block unchanged.
2. Build CME sample MBO replay and iceberg-like/replenishment diagnostics.
3. Connect permitted Bookmap CME MBO and validate live feature parity.
4. Build SPX/SPXW unusual-options and whale-flow anomaly engine.
5. Add legally/timely available off-exchange inputs.
6. Test each family incrementally against existing GEXY forecasts.
7. Add only prospectively validated information to the calibrated multi-expert ensemble.

## Guiding principle

GEXY should detect important market activity without romanticizing it. `Whale`, `unusual`, `iceberg`, and `dark-pool` labels are useful only when they are precisely defined, causally observable, independently tested, and shown to add predictive information on untouched future data.
