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

## Interpretation rule

- Same negative sign across additional days strengthens evidence of stability.
- Sign reversals or collapse toward zero are evidence against universality of the current relationship and must be reported.
- Day-level consistency matters more than selecting the best individual minute feature.
- The current relationship remains a proxy association, not proof of dealer inventory, executed hedge flow, causality, or trading profitability.
