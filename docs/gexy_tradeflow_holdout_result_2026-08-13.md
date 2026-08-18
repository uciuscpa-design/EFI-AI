# GEXY trade-flow holdout result — 2026-08-13

## Status

This document records the first pre-specified out-of-sample GEXY TCBBO trade-flow holdout result. The holdout protocol, data scope, classifier, causal timing, Greek solver, 90% classified-volume Greek coverage floor, horizons, and primary endpoints were frozen before the 2026-08-13 TCBBO was downloaded or inspected.

The holdout is evaluated exactly as specified. No alternate signal is substituted because it performed better.

## Data quality

- Holdout date: 2026-08-13
- Frozen windows: 09:30-10:00 and 15:30-16:00 America/New_York
- Strike scope: opening-forward +/- 200 SPX points
- Greek symbol-minute snapshots: 3,733
- Greeks solved: 3,320 / 3,733 = 88.9%
- Median classified contract volume with usable Greeks: 99.7%
- Completed hedge-flow minutes: 60
- Replay-matched availability minutes: 57 / 60
- The opening availability minute at 13:31 UTC had 0% Greek-volume coverage and was excluded by the frozen 90% volume-coverage floor.

## Primary pre-specified endpoints

Both primary endpoints use the fixed `net_contracts_vs_delta` pair and report `hedge_delta_units` rank-partial Spearman after controlling for:

1. the completed flow-minute SPX return (`backward_return_1m_bps`), and
2. raw net signed option contracts (`flow_net_signed_contracts`).

| Horizon | Discovery 2026-08-12 | Holdout 2026-08-13 | Holdout observations | Sign replicated? |
|---|---:|---:|---:|---|
| 5 minutes | -0.1997 | -0.1830 | 51 | Yes |
| 15 minutes | -0.2519 | -0.2032 | 41 | Yes |

### Primary verdict

The first holdout **replicates the negative sign at both frozen primary horizons**, with magnitudes similar to the discovery day. Under the pre-specified protocol, this is evidence of short-sample stability of the net delta-weighted relationship. It is not proof of causality or trading edge.

The result remains opposite the simplest mechanical continuation story: positive `hedge_delta_units` means estimated opposite-side liquidity-provider hedge buying, yet larger positive values were associated with lower subsequent SPX returns after the two controls.

## Raw-flow comparison on the holdout

Raw net signed contracts were themselves strongly negative on 2026-08-13:

- 5-minute raw Spearman: -0.3662
- 5-minute raw partial Spearman controlling for the completed 1-minute SPX move: -0.3383
- 15-minute raw Spearman: -0.5321
- 15-minute raw partial Spearman controlling for the completed 1-minute SPX move: -0.4957

Therefore, the holdout does **not** show that Greek weighting is uniformly stronger than raw flow. The relevant incremental result is narrower: after controlling for both momentum and the paired raw-flow signal, net delta weighting still retains negative residual association (-0.1830 at 5 minutes and -0.2032 at 15 minutes).

## Secondary pre-specified decomposition

The secondary decomposition was not fully stable across days.

### 5-minute call delta

- Discovery partial Spearman after both controls: approximately -0.176
- Holdout partial Spearman after both controls: +0.0046

The pre-specified 5-minute call-delta decomposition **did not replicate**; it collapsed to approximately zero and changed sign slightly.

### 15-minute put delta

- Discovery partial Spearman after both controls: approximately -0.225
- Holdout partial Spearman after both controls: -0.3505

The pre-specified 15-minute put-delta decomposition **did replicate the negative sign** and was stronger in magnitude on the holdout.

### Decomposition verdict

The primary net-delta relationship is more stable than the call/put attribution. Do not conclude that a single call-side or put-side mechanism is established. The composition of the net relationship changed materially across the two days.

## Lead/lag context

At the frozen 90% Greek-volume coverage floor on the holdout:

- `hedge_delta_units` absolute Spearman with the contemporaneous flow-minute move: 0.2979
- with forward 5-minute return: 0.1236
- with forward 15-minute return: 0.1645

This indicates substantial contemporaneous/reactive content. The incremental partial-correlation result is therefore the more relevant diagnostic for forward information than the ordinary hedge-flow correlation.

## Interpretation

Supported by this first holdout:

- The negative 5-minute and 15-minute net delta-weighted partial relationship survived an untouched next-day test.
- The relationship survives controls for the just-completed 1-minute SPX move and raw net signed option contracts.
- The sign is stable across the discovery day and first holdout.

Not supported yet:

- Causality from dealer hedging to SPX movement.
- A claim that Greek weighting always outperforms raw flow.
- A stable call-versus-put decomposition at all horizons.
- A production trading edge.
- Statistical independence of minute observations; forward horizons overlap heavily.

## Next research rule

Treat the 2026-08-12 discovery day and 2026-08-13 first holdout as completed evidence. Any post-holdout mechanism analysis may use them as research data, but a changed signal definition must be validated on a later untouched day before being called out-of-sample.

Before purchasing more TCBBO, the next work should be local-only and should quantify stability under overlapping observations and day-level variation using fixed primary endpoints. Do not tune the aggressor classifier or reverse the hedge sign convention in response to these results.
