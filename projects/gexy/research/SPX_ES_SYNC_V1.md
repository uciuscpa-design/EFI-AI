# GEXY — SPX/ES Point-in-Time Synchronization v1

**Status:** research infrastructure; provider-neutral ES integration pending  
**Frozen design date:** 2026-08-14  
**Execution:** disabled  
**Production predictor:** unchanged

## Purpose

Create a leakage-safe synchronization contract for pairing GEXY's inferred SPX reference with a real ES futures observation once an approved ES market-data source is connected.

This layer is infrastructure only. It does not create a trading signal and does not authorize a new feature merely because synchronized observations exist.

## Current SPX reference provenance

The current Alpaca live path does not observe SPX cash directly. GEXY infers an SPX reference from same-strike call/put midpoint parity:

`SPX_reference ~= strike + call_mid - put_mid`

The point estimate is the median across matched parity estimates.

For point-in-time work, GEXY must preserve the exact quote timestamps of the selected median call/put pair. The inferred SPX value is considered available only at the **later** of those required source quote timestamps.

The collector/acquisition timestamp is preserved separately and must not be represented as the SPX market-event timestamp.

## ES source requirement

No SPY or other equity proxy may be labeled as ES.

A future ES adapter must provide, at minimum:

- exact futures contract symbol, including expiry/roll identity;
- provider/source identity;
- price used by the feature (trade, bid/ask midpoint, or another explicitly named field);
- provider/event timestamp;
- GEXY receive/acquisition timestamp;
- contract-roll metadata where applicable.

Until a real ES source satisfies this contract, SPX/ES synchronized features remain unavailable rather than fabricated.

## Frozen v1 join rule

For each inferred SPX observation:

1. Set the SPX anchor to the later timestamp of the call/put quotes required by the selected parity pair.
2. Consider only ES observations with `es.observed_at <= spx_anchor_at`.
3. Select the latest eligible ES observation.
4. Never use nearest-neighbor matching that can select a future ES row.
5. Never interpolate across a future ES observation.
6. Default maximum accepted ES lag: **5.0 seconds**.
7. If no eligible ES row exists, status is `missing_reference` and the pair is unscoreable.
8. If the latest eligible ES row is older than the lag limit, status is `stale_reference` and the pair is unscoreable, though the stale row is retained for diagnostics.
9. Only `matched` rows may feed a later research feature experiment.

## Provenance fields

Every serialized synchronized pair must preserve:

- primary symbol, instrument type and price;
- primary provider/event timestamp;
- primary receive/acquisition timestamp;
- primary source;
- reference symbol, instrument type and price;
- reference provider/event timestamp;
- reference receive/acquisition timestamp;
- reference source;
- reference lag in seconds;
- configured maximum lag;
- scoreability;
- explicit `no_lookahead_enforced=true` marker.

## Research boundary

The synchronization layer does **not** yet define an ES predictive feature. In particular, raw ES-SPX basis, ES momentum, lead/lag, order-flow imbalance or liquidity features must each be introduced through a versioned research hypothesis with chronological validation.

The futures/cash basis is affected by financing, dividends, time to expiry and contract roll. GEXY must not assume a raw price difference is a universal directional signal.

## Validation requirements before any ES-derived feature is considered

- real provider-labeled ES data, not a proxy mislabeled as futures;
- point-in-time joins using the frozen v1 rule;
- timestamp-lag distribution and missing/stale coverage report;
- explicit roll handling;
- chronological train/validation/test or independent-session evaluation;
- comparison against simple baselines;
- no production predictor change from exploratory same-session results;
- execution remains disabled.

## Implemented code

- `packages/gexy/market_sync.py`
  - `MarketObservation`
  - `inferred_spot_observation`
  - `latest_at_or_before`
  - `synchronize_primary_with_reference`
  - `synchronize_series`
  - `pair_to_record`
- `packages/gexy/alpaca_provider.py`
  - preserves quote timestamps for the exact parity pair selected by the median SPX estimator.
- `packages/gexy/alpaca_live.py`
  - exposes the parity-pair quote timestamps separately from the broader usable option-quote timestamp set.
- `scripts/gexy_live_predict.py`
  - emits explicit SPX spot provenance in the research/collector payload.
- `tests/test_gexy_market_sync.py`
- `tests/test_gexy_alpaca_provider.py`

## Next integration step

Connect an approved real ES futures market-data adapter to `MarketObservation`, then collect paired SPX/ES records without yet feeding them into the production predictor. The first report should measure synchronization quality and coverage only.
