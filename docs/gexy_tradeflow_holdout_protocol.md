# GEXY trade-flow holdout protocol

## Purpose

Freeze the next validation step before inspecting another day's TCBBO trade flow. The 2026-08-12 pilot is discovery data only. The next TCBBO day is a holdout and must use the same classifier, windows, strike selection, causal alignment, Greek solver, coverage floor, and diagnostics without tuning after seeing the holdout result.

## Discovery day

- Date: 2026-08-12
- TCBBO windows: 09:30-10:00 and 15:30-16:00 America/New_York
- Strike scope: opening-forward +/- 200 SPX points
- Trade direction: frozen pre-trade NBBO classifier
- Feature availability: minute-M flow becomes available at M+1
- Greek-volume quality floor for incremental diagnostics: 90%
- Discovery data are not an out-of-sample validation set.

### Frozen discovery observations

For the fixed `net_contracts_vs_delta` pair after controlling for both the completed flow-minute SPX return and raw net signed contracts:

- 5-minute partial Spearman: approximately -0.200
- 15-minute partial Spearman: approximately -0.252

Decomposition observed on the discovery day:

- 5-minute call-delta partial Spearman after both controls: approximately -0.176
- 5-minute put-delta partial Spearman after both controls: approximately -0.004
- 15-minute call-delta partial Spearman after both controls: approximately -0.033
- 15-minute put-delta partial Spearman after both controls: approximately -0.225

The sign is opposite the simplest mechanical continuation story. Positive `hedge_delta_units` means estimated opposite-side liquidity-provider hedge buying, yet the discovery-day 5- and 15-minute forward associations were negative. This may represent reaction, absorption, reversal, incorrect dealer-side assumptions, or another mechanism. Do not relabel the sign after seeing holdout data.

## Holdout day

Primary holdout date: **2026-08-13**, the next trading session after the discovery day.

Use exactly:

- TCBBO windows: 09:30-10:00 and 15:30-16:00 America/New_York
- strike scope: opening-forward +/- 200 SPX points
- same raw-symbol selection logic
- same frozen aggressor classifier
- same M+1 causal availability rule
- same Black-76 forward/IV/delta/gamma calculations
- same 90% classified-volume Greek coverage floor
- same horizons: 1, 5, 15, 30, 60 minutes

Do not alter any of those rules after viewing 2026-08-13 TCBBO results.

## Primary holdout endpoints

The primary endpoints are fixed before downloading the holdout TCBBO:

1. `hedge_delta_units` partial Spearman versus the 5-minute forward return, controlling for:
   - `backward_return_1m_bps`
   - `flow_net_signed_contracts`
2. `hedge_delta_units` partial Spearman versus the 15-minute forward return with the same controls.

Expected discovery sign for both: **negative**.

Secondary pre-specified decomposition:

- 5-minute `hedge_call_delta_units` partial Spearman, expected discovery sign negative.
- 15-minute `hedge_put_delta_units` partial Spearman, expected discovery sign negative.

## Reporting rules

Report all fixed endpoints whether favorable or unfavorable. Also report:

- observations after the 90% volume-coverage filter
- momentum Spearman
- raw-flow Spearman and raw-flow partial Spearman controlling for momentum
- hedge-flow ordinary Spearman
- hedge-flow partial Spearman controlling for momentum
- hedge-flow partial Spearman controlling for momentum plus paired raw flow
- Greek symbol coverage and classified-volume Greek coverage
- any missing replay minutes or zero-Greek-coverage minutes

Do not select a different signal because it performs better on the holdout.

## Interpretation rules

- Same-sign replication across the 5- and 15-minute primary endpoints is evidence of stability, not proof of causality.
- Sign reversal or collapse toward zero is evidence against the current discovery hypothesis and should trigger mechanism review before buying more days.
- Strong contemporaneous correlation does not count as predictive evidence.
- Longer-horizon results have fewer and overlapping observations and remain secondary.
- OPRA does not identify dealer inventory or executed hedge trades; all dealer/LP hedge quantities remain explicit proxies.

## Spend guardrail

Before purchasing the 2026-08-13 TCBBO holdout, run the metadata-only dry-run with the same bounded windows and +/-200 strike band. Keep the requested execution cap at **$4.00**. If the exact re-priced holdout estimate exceeds $4.00, do not raise the cap automatically; review or narrow the request first.

### Pre-download reviewed exception — 2026-08-15

The frozen 2026-08-13 holdout dry-run was completed before any holdout TCBBO was downloaded or inspected. The exact estimate was **$4.002663** for the unchanged two-window, +/-200-point, 160-symbol request: $2.365129 for 09:30-10:00 and $1.637533 for 15:30-16:00.

This exceeds the original requested $4.00 cap by **$0.002663** (about 0.0666%). Narrowing the windows, strike band, or symbol set solely to fit the original cap would change the pre-specified holdout sample. After review, the holdout data specification and all statistical hypotheses remain unchanged; only the operational requested execution cap is raised to **$4.05** for this one holdout download. The downloader's independent **$5.00 hard safety ceiling** remains unchanged, and the exact cost must still be re-checked immediately before download. If the re-priced request exceeds $4.05, the download must be refused and reviewed again.
