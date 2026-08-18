# GEXY Whale / Unusual-Options / Iceberg / Off-Exchange Intelligence

## Status

Official supporting research charter for the GEXY S&P 500 Total-Market Intelligence roadmap.

The **off-exchange/TRF software foundation is now implemented in isolation**. It is not connected to the frozen 2026-08-17 through 2026-08-21 prospective replication, and it may not influence that protocol, its features, its labels, or its adjudication. Forecast activation, threshold freezing, incremental-value testing, and ensemble use remain deferred until the frozen prospective replication is completed and formally recorded.

Implemented foundation:

- `packages/gexy/off_exchange.py` — explicit off-exchange normalization, causal large-print classification, completed-minute TRF/off-exchange features, prior-only anomaly scoring, and replay-join support;
- `scripts/gexy_off_exchange_features.py` — local-CSV feature builder that makes no paid market-data requests;
- `tests/test_gexy_off_exchange.py` — tests for explicit venue identification, no buyer/seller inference, prior-only large-print baselines, M+1 availability, and future-data non-contamination.

Local verification on 2026-08-17:

```text
uv run --with pandas --with pytest pytest -q tests/test_gexy_off_exchange.py
..... [100%]
5 passed in 22.46s
```

Interpretation: the isolated off-exchange/TRF unit-test suite passed locally. This verifies the tested software contracts only; it does not establish predictive value, calibration, economic value, or prospective forecasting validity.

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

- off-exchange share volume and notional;
- unusually large prints relative to the instrument's prior causal distribution;
- repeated prints near the same price level;
- price-level persistence after large prints;
- constituent and ETF clustering;
- timing relative to SPX option-flow shocks, ES MBO changes, and subsequent index movement;
- delayed-reporting awareness and exact `available_at` timestamps.

Off-exchange NMS-stock executions can include ATS/dark-pool trades and broker-dealer internalization reported through FINRA facilities and disseminated to the consolidated market-data system. The observable tape can support price, size, time, and reporting-venue/facility analysis, but it generally does not identify the specific beneficial buyer/seller or prove informed intent.

GEXY must **not** hard-code a generic exchange/condition code such as `D` as synonymous with dark pool or TRF. Source adapters must provide an explicit off-exchange marker or an explicit allow-list of reporting venue/publisher identifiers appropriate to that feed. The core module refuses to guess from print size, price behavior, or generic condition codes.

For Databento-style feeds, the adapter should preserve the source publisher/reporting identifier and explicitly select the FINRA/TRF publishers appropriate to the licensed dataset. The core analytics remain provider-neutral and accept explicit publisher values rather than embedding vendor-specific IDs in the research logic.

Dark/off-exchange prints must never be treated as real-time predictive information before they were actually disseminated. GEXY must not infer buyer/seller identity or institutional intent unless the source explicitly provides it.

### 4.1 Implemented causal feature contract

The current off-exchange foundation implements these rules:

1. **Explicit identification only** — a source-provided boolean marker or explicit venue/publisher allow-list is required.
2. **Strict `available_at` causality** — the source timestamp passed to the core must represent when the print was observable to GEXY, not an unavailable earlier execution time.
3. **Completed-minute alignment** — prints observed during minute M become minute features at M+1.
4. **Prior-only large-print baseline** — a print is classified as large only against earlier prints in the same symbol; the current and future prints cannot enter its threshold.
5. **No direction mythology** — the module does not create buyer/seller, bullish/bearish, institutional, smart-money, or specific-dark-pool identity fields.
6. **Repeated-level diagnostics** — same-symbol/same-price repeats are measured as observable clustering, not assumed accumulation/distribution.
7. **Non-directional anomaly score** — volume, notional, and large-print-volume anomalies are measured against prior completed minutes. `unusual` is not synonymous with `predictive`.
8. **Replay join is available but inactive** — the core can join completed-minute features to GEXY replay state for later walk-forward research, but the new module is not wired into the frozen Aug. 17-21 prospective validator or ensemble.

Current feature family includes:

- `offx_trade_records`;
- `offx_unique_symbols`;
- `offx_share_volume`;
- `offx_notional`;
- `offx_mean_print_size`;
- `offx_max_print_size`;
- `offx_large_print_records`;
- `offx_large_print_volume`;
- `offx_large_print_notional`;
- `offx_large_print_volume_share`;
- `offx_repeated_level_groups`;
- `offx_repeated_level_volume`;
- `offx_repeated_level_volume_share`;
- causal robust anomaly diagnostics;
- `off_exchange_anomaly_score`.

## 5. Cross-signal fusion

Test whether these families provide incremental information when combined with existing GEXY experts. Example causal sequence:

`unusual SPXW flow -> inferred hedge pressure -> ES MBO replenishment / depletion -> breadth confirmation -> subsequent SPX movement`

Additional off-exchange sequence to test after the frozen block:

`TRF/off-exchange print cluster -> SPY/constituent level persistence -> ES MBO response -> SPX/SPXW option-flow agreement/disagreement -> subsequent index movement`

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
- Keep the implemented off-exchange foundation disconnected from the frozen 2026-08-17 through 2026-08-21 protocol until that result is formally recorded.

## Development order

1. Finish and record the frozen Aug. 17-21 prospective block unchanged.
2. Build CME sample MBO replay and iceberg-like/replenishment diagnostics.
3. Connect permitted Bookmap CME MBO and validate live feature parity.
4. Build SPX/SPXW unusual-options and whale-flow anomaly engine.
5. Validate the implemented off-exchange/TRF foundation against licensed historical/local data and freeze a source adapter contract.
6. Test off-exchange features alone for incremental walk-forward value before cross-signal fusion.
7. Test each family incrementally against existing GEXY forecasts.
8. Add only prospectively validated information to the calibrated multi-expert ensemble.

## Guiding principle

GEXY should detect important market activity without romanticizing it. `Whale`, `unusual`, `iceberg`, and `dark-pool` labels are useful only when they are precisely defined, causally observable, independently tested, and shown to add predictive information on untouched future data.
