# GEXY trade-flow validation batch 2 protocol

## Purpose

Freeze the next untouched TCBBO validation sessions before pricing or inspecting their trade-flow data. This prevents selecting a validation date because it produces a favorable result.

The completed evidence set is:

- discovery: 2026-08-12
- first pre-specified holdout: 2026-08-13

The next validation batch uses three previously uninspected TCBBO days that already have cached GEXY replay/chain inputs.

## Frozen validation dates and order

Evaluate in this fixed order:

1. 2026-08-11
2. 2026-08-10
3. 2026-08-07

Do not substitute another date because of signal performance. Cost review may determine how many of the frozen dates are purchased, but any purchased dates must follow the order above.

## Frozen data scope

For every purchased validation day use exactly:

- SPXW 0DTE
- TCBBO
- windows: 09:30-10:00 and 15:30-16:00 America/New_York
- strike scope: opening-forward +/- 200 SPX points
- same raw-symbol selection logic
- same frozen pre-trade NBBO aggressor classifier
- same M+1 completed-minute causal availability rule
- same Black-76 forward/IV/delta/gamma calculations
- same 90% classified-volume Greek coverage floor
- same horizons: 1, 5, 15, 30, 60 minutes

No classifier, sign, Greek solver, timing, window, strike, or coverage change may be made in response to validation results.

## Primary endpoints

Report first, for every validation day:

1. 5-minute `net_contracts_vs_delta` — `hedge_delta_units` rank-partial Spearman controlling for:
   - `backward_return_1m_bps`
   - `flow_net_signed_contracts`
2. 15-minute `net_contracts_vs_delta` with the same controls.

The existing two-day evidence has negative sign at both horizons. The validation question is whether those same fixed endpoints remain stable; do not redefine the expected sign after seeing a new day.

## Secondary reporting

Also report, without replacing the primary endpoints:

- observations after the 90% Greek-volume coverage filter
- Greek symbol-minute solve rate
- classified-volume Greek coverage
- replay-match count
- raw net-flow Spearman and raw partial Spearman controlling momentum
- ordinary hedge Spearman
- hedge partial Spearman controlling momentum
- lead/lag table
- deterministic non-overlapping sensitivity once enough days exist

## Cost rule

Before any purchase, run metadata-only cost estimation for all three frozen dates. Pricing does not inspect TCBBO records and does not count as validation-result exposure.

No TCBBO download should occur during the pricing step. After costs are known, purchases may proceed only in the frozen date order. A skipped date due to budget must be recorded as a budget decision, not silently replaced by a cheaper or more favorable date.

### Metadata pricing and pre-purchase budget decision — 2026-08-15

Metadata-only pricing was completed for all three frozen dates before any batch-2 TCBBO was downloaded or inspected.

Estimated bounded costs using the unchanged two windows, +/-200-point strike band, and 160 exact symbols per day:

- 2026-08-11: 09:30-10:00 $1.895586 + 15:30-16:00 $2.008177 = **$3.903763**
- 2026-08-10: 09:30-10:00 $1.551260 + 15:30-16:00 $1.754614 = **$3.305874**
- 2026-08-07: 09:30-10:00 $2.071825 + 15:30-16:00 $1.891112 = **$3.962937**
- total estimated batch cost: **$11.172574**

The budget decision is frozen before seeing any batch-2 validation result: purchase **all three dates** in the pre-specified order 2026-08-11, 2026-08-10, 2026-08-07, provided each date remains within its reviewed operational cap at the downloader's immediate pre-download re-price. Do not stop the batch early because an intermediate validation result is favorable or unfavorable.

Reviewed operational caps are:

- 2026-08-11: **$3.95**
- 2026-08-10: **$3.35**
- 2026-08-07: **$4.00**

The downloader's independent absolute safety ceiling remains **$5.00 per invocation**. If a date re-prices above its reviewed operational cap, refuse that download and record a new budget review before changing the cap. Such a budget exception must not change the frozen data scope or primary endpoints.

### Acquisition record — 2026-08-11

The first batch-2 date was purchased on 2026-08-15 before any 2026-08-11 trade-flow classification, Greek weighting, feature scoring, or endpoint analysis was performed.

The immediate pre-download re-price remained **$3.903763**, within the frozen **$3.95** operational cap:

- 09:30-10:00 America/New_York: $1.895586
- 15:30-16:00 America/New_York: $2.008177
- total pre-download estimate: **$3.903763**

Both unchanged 160-symbol windows were cached successfully. The batch remains committed to continue in the frozen order with 2026-08-10 and then 2026-08-07 before any batch-2 signal result is inspected. No early stopping is permitted based on intermediate results.

### Acquisition record — 2026-08-10

The second batch-2 date was purchased on 2026-08-15 before any 2026-08-10 trade-flow classification, Greek weighting, feature scoring, or endpoint analysis was performed.

The immediate pre-download re-price remained **$3.305874**, within the frozen **$3.35** operational cap:

- 09:30-10:00 America/New_York: $1.551260
- 15:30-16:00 America/New_York: $1.754614
- total pre-download estimate: **$3.305874**

Both unchanged 160-symbol windows were cached successfully. No 2026-08-11 or 2026-08-10 batch-2 signal result has been inspected. The batch remains committed to purchase the final frozen date, 2026-08-07, before any batch-2 extraction, Greek weighting, feature scoring, or endpoint analysis. No early stopping is permitted based on intermediate results.

### Acquisition record — 2026-08-07 and batch completion

The final batch-2 date was purchased on 2026-08-15 before any batch-2 trade-flow extraction, Greek weighting, feature scoring, or endpoint analysis was performed.

The immediate pre-download re-price remained **$3.962937**, within the frozen **$4.00** operational cap:

- 09:30-10:00 America/New_York: $2.071825
- 15:30-16:00 America/New_York: $1.891112
- total pre-download estimate: **$3.962937**

Both unchanged 160-symbol windows were cached successfully. Batch-2 acquisition is now complete for all three pre-specified dates. Total pre-download estimated cost across the batch was **$11.172574**. No 2026-08-11, 2026-08-10, or 2026-08-07 batch-2 signal result was inspected before all three acquisitions were completed.

From this point forward, process all three dates only through the frozen pipeline and report the fixed 5-minute and 15-minute primary endpoints before considering any secondary or post-batch research result.

## Interpretation rule

- Same negative sign across additional days strengthens evidence of stability.
- Sign reversals or collapse toward zero are evidence against universality of the current relationship and must be reported.
- Day-level consistency matters more than selecting the best individual minute feature.
- The current relationship remains a proxy association, not proof of dealer inventory, executed hedge flow, causality, or trading profitability.
