# GEXY — ES Market-Data Provider Selection v1

**Decision date:** 2026-08-14  
**Status:** research integration selected; credentials/subscription not yet provisioned  
**Preferred provider:** Databento  
**Preferred dataset:** `GLBX.MDP3`  
**Initial ES selector:** `ES.v.0` with `stype_in=continuous`  
**Initial schema:** `trades`  
**Production predictor:** unchanged  
**Execution:** disabled

## Decision

Use **Databento** as the preferred first real ES futures source for GEXY's research synchronization layer.

Massive Futures remains a viable alternative if pricing, account availability, or operational constraints make Databento unsuitable. No proxy such as SPY may be substituted and labeled as ES.

## Why Databento is the preferred fit

GEXY's highest-priority requirement is not simply obtaining an ES price. It is obtaining a point-in-time ES observation with enough provenance to prove that historical/replay joins did not use future data.

Databento's CME Globex dataset exposes distinct event and provider-receive timestamps (`ts_event` and `ts_recv`) on trade and book records. That maps directly to GEXY's event-time versus acquisition-time model.

Databento also supports:

- CME Globex futures through `GLBX.MDP3`;
- live and historical ES data;
- parent and continuous futures symbology;
- point-in-time mapping from continuous/smart symbols to actual raw contracts;
- explicit instrument IDs and publisher IDs;
- live symbol-mapping messages that can preserve actual contract identity through rolls.

## Initial v1 data choice

Start with the `trades` schema rather than immediately introducing order-book logic.

Reason:

- trade records have an unambiguous event price and documented fixed-point representation;
- they expose both `ts_event` and `ts_recv`;
- this is enough to validate synchronization coverage and latency before introducing bid/ask or order-flow features;
- ES is typically liquid enough during the SPX cash session for trade-event coverage to be measured empirically rather than assumed.

A later version may use `mbp-1` for best bid/offer, spread, liquidity, and order-flow research, but only after the trade-based synchronization layer passes integrity and coverage checks.

## Contract-roll handling

The research selector is `ES.v.0` using continuous symbology, but every persisted event must record the **actual raw contract symbol** and `instrument_id` supplied by the contemporaneous symbol mapping.

GEXY must not treat `ES.v.0` itself as a tradable contract identity.

The adapter therefore requires a point-in-time mapping before accepting a trade. A mapping timestamp later than the trade event is rejected as lookahead. Raw-symbol or instrument-ID mismatches are rejected.

For live operation, roll/mapping behavior must be actively handled rather than assumed to remap a long-running subscription invisibly. The collector should refresh/confirm mapping state at each session and record every mapping transition.

## Timestamp semantics

For each Databento trade:

- `ts_event` -> ES market event timestamp used for point-in-time synchronization;
- `ts_recv` -> Databento capture-server receive timestamp, retained for provider-latency diagnostics;
- GEXY receive time -> local acquisition timestamp retained separately;
- SPX anchor -> later quote timestamp of the exact call/put parity pair used to infer SPX;
- valid ES join -> latest ES event with `ES.ts_event <= SPX.anchor_time`, subject to the frozen lag limit.

## Price semantics

The first adapter uses trade price. Databento DBN fixed-point prices are normalized using the documented `1e-9` scale before they become a GEXY `MarketObservation`.

No bid/ask midpoint, settlement, synthetic continuous adjustment, or back-adjusted price is substituted for the trade price in v1.

## Activation gate

Before live ES collection can begin:

1. A Databento account/API key must be provisioned by the user.
2. The Python client dependency and credential must be configured locally without committing the key.
3. A read-only connectivity/preflight check must succeed.
4. The returned symbol mapping must identify a real ES futures contract.
5. `ts_event`, `ts_recv`, raw symbol, instrument ID, price, and GEXY receive time must all be persisted.
6. The synchronization coverage report must show zero lookahead violations.

## Research gate after activation

The first ES-enabled sessions are **coverage/integrity collection only**. They do not change predictions.

Before any ES-derived signal is tested, GEXY must report:

- matched/stale/missing synchronization counts;
- scoreable fraction;
- lag mean/max/p95;
- contract identity and roll transitions;
- provider/GEXY latency diagnostics;
- zero lookahead violations.

Only after that may a separately versioned hypothesis define an ES-derived feature such as momentum, lead/lag, basis deviation, trade imbalance, or liquidity.

## Implemented boundary

`packages/gexy/databento_es.py` currently implements the credential-free normalization boundary:

- `DatabentoEsConfig`
- `DatabentoSymbolMapping`
- `DatabentoTradeEvent`
- fixed-point price normalization
- `ts_event` / `ts_recv` preservation
- mapping mismatch and future-mapping rejection
- conversion to provider-neutral `MarketObservation`
- vendor-specific provenance serialization

Networking/authentication is deliberately not implemented until a real API key exists. This prevents the project from pretending that ES is connected before it actually is.
