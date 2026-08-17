# GEXY Bookmap / CME MBO integration roadmap

## Status

Standing implementation recommendation for GEXY. This roadmap is intentionally deferred until it can be added without altering or contaminating the frozen 2026-08-17 through 2026-08-21 prospective SPXW replication.

## Objective

Use CME futures Market By Order (MBO) data, preferably through the user's existing Bookmap CME feed where licensing permits, as a lower-cost microstructure confirmation layer for GEXY while retaining the minimum necessary OPRA/SPXW options data for the options-derived GEX/GAX and hedge-pressure calculations.

CME/Bookmap MBO is not a replacement for OPRA SPX/SPXW options data. It is a complementary source for observing ES futures order-book response.

## Planned architecture

1. OPRA/SPXW options input
   - option trades and pre-trade consolidated BBO;
   - same frozen aggressor inference;
   - forward/IV/Black76 Greek calculations;
   - GEX/GAX and `hedge_delta_units` proxy construction.

2. CME ES MBO input
   - full order-book add/replace/cancel events where available;
   - trade events and queue changes;
   - anonymous order-level market structure only; no participant/dealer identity claims.

3. GEXY MBO / hedge-response feature engine
   - bid/ask queue imbalance;
   - depth-weighted pressure;
   - add/cancel velocity;
   - queue depletion and replenishment;
   - aggressive trade imbalance;
   - sweep intensity;
   - microprice / book-pressure measures;
   - large-order and iceberg-related diagnostics where supported by observable events;
   - short-horizon ES response features.

4. Fusion research question

Test whether SPX option-derived hedge-pressure estimates at time M are followed by causal future ES MBO changes at M+1 through M+n and then by subsequent SPX/ES movement. Preserve strict timestamp causality and do not infer that anonymous CME orders are dealers.

## Development order

### Phase A — free/sample MBO laboratory

Before using live Bookmap data, build a deterministic CME MBO parser/replayer against available CME sample files. Validate book reconstruction, queue accounting, add/cancel/replace logic, and derived feature calculations.

### Phase B — Bookmap adapter

After the sample replay is validated, implement a local Bookmap-to-GEXY adapter using the supported Bookmap futures/MBO interfaces available to the user's subscription. Prefer local feature computation rather than exporting or redistributing raw MBO.

### Phase C — record/replay archive

Record permitted live MBO locally so GEXY can accumulate its own forward research history over time. Keep raw-data retention and redistribution within Bookmap/CME licensing terms.

### Phase D — synchronized OPRA + ES MBO research

Align SPXW option-derived hedge proxies with ES MBO features using causal timestamps. Evaluate whether MBO adds incremental predictive information beyond the existing GEXY option-flow pipeline.

### Phase E — production cost optimization

If Bookmap/CME MBO provides the required futures microstructure feed reliably and licensing permits local GEXY use, avoid purchasing redundant CME MBO from another vendor. Continue paying only for the OPRA/SPXW inputs that cannot be replaced by CME futures data.

## Scientific constraints

- Do not modify the frozen 2026-08-17 through 2026-08-21 prospective protocol based on MBO findings.
- CME MBO is anonymous; do not identify dealer/customer ownership from order IDs.
- `hedge_delta_units` remains an inferred LP/dealer hedge proxy, not observed dealer inventory or executed hedge flow.
- Any post-prospective MBO feature selection must be labeled developmental/post-hoc unless separately frozen before a new forward block.
- Preserve exact timestamp causality for all MBO-to-return tests.

## Cost principle

Reuse the user's existing Bookmap CME MBO entitlement where technically and contractually permitted to minimize redundant live-data expense. Use CME sample data first for parser/replay development. Maintain OPRA/SPXW acquisition only for the options information that CME futures MBO cannot supply.
