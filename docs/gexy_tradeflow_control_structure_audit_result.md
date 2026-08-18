# GEXY batch-3 control-structure audit result

## Status

This document records the local-only post-validation control-structure audit frozen after batch-3 validation and after the separate data-quality audit. It does not change the batch-3 verdict: the opening 15-minute primary endpoint remains a partial replication, negative on 2/3 untouched sessions and positive on 2026-08-06 under the frozen two-control definition.

Dates:

1. 2026-08-06
2. 2026-08-05
3. 2026-08-04

Unchanged scope:

- opening 09:30-10:00 America/New_York
- 90% classified-volume Greek coverage floor
- horizons 5 and 15 minutes
- hedge signal: `hedge_delta_units`
- raw control: `flow_net_signed_contracts`
- momentum control: `backward_return_1m_bps`

## Results

| Trading day | Horizon | Hedge vs target | Raw vs target | Momentum vs target | Hedge vs raw | Hedge vs momentum | Raw vs momentum | Hedge | momentum | Hedge | raw | Hedge | momentum + raw | Ordinary-to-both sign flip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-06 | 5m | -0.016256 | -0.151232 | -0.225123 | +0.358128 | +0.367980 | -0.125123 | +0.073496 | +0.041069 | +0.175254 | yes |
| 2026-08-06 | 15m | -0.209360 | -0.514286 | -0.193103 | +0.358128 | +0.367980 | -0.125123 | -0.151591 | -0.031445 | +0.121166 | yes |
| 2026-08-05 | 5m | -0.248276 | +0.015271 | -0.088177 | +0.126601 | +0.248276 | +0.130049 | -0.234615 | -0.252268 | -0.238513 | no |
| 2026-08-05 | 15m | -0.486700 | +0.307389 | -0.271429 | +0.126601 | +0.248276 | +0.130049 | -0.449748 | -0.556839 | -0.522197 | no |
| 2026-08-04 | 5m | -0.375862 | +0.047291 | -0.194581 | +0.307389 | +0.681281 | +0.126108 | -0.338840 | -0.410722 | -0.380469 | no |
| 2026-08-04 | 15m | -0.418719 | +0.255665 | -0.308374 | +0.307389 | +0.681281 | +0.126108 | -0.299606 | -0.540576 | -0.436355 | no |

## Primary 15-minute interpretation

The failed 2026-08-06 session does **not** show an ordinary reversal of the hedge proxy. The ordinary hedge/15-minute association is negative (-0.209360). It remains negative when controlling only momentum (-0.151591) and remains slightly negative when controlling only raw signed contracts (-0.031445). The sign turns positive (+0.121166) only when both controls are included simultaneously.

This matches the pre-frozen protocol condition for a possible multivariable suppression/residualization effect. It does not prove classical collinearity: the pairwise rank correlations are moderate rather than extreme (`hedge_raw` +0.358128, `hedge_momentum` +0.367980, `raw_momentum` -0.125123). The correct interpretation is therefore that the Aug 6 frozen residual endpoint is **control-structure sensitive**, with the joint rank residualization changing the sign.

In contrast, the 15-minute relationship on 2026-08-05 and 2026-08-04 is robustly negative under the ordinary association, each single-control specification, and the frozen two-control specification. Their two-control values remain -0.522197 and -0.436355 respectively.

The 5-minute Aug 6 endpoint is less informative mechanistically because its ordinary association is already near zero (-0.016256) and turns positive under either single control. The primary research focus remains 15 minutes.

## Scientific consequence

Batch 3 remains **partial replication, not a clean validation**. Aug 6 must remain a failed frozen-endpoint day and must not be removed because the ordinary or single-control associations look more favorable.

At the same time, the audit shows that the failed day is best characterized as a failure of the **incremental two-control residual endpoint**, not a wholesale opposite-signed hedge-flow relationship. This narrows the next research question from generic market-regime hunting to stability of the control structure across all existing opening-window sessions.

## Next rule

Before purchasing any more TCBBO or proposing a conditional trading rule, run a local-only opening-window control-stability analysis across all eight existing sessions (2026-08-04 through 2026-08-13 excluding the weekend), using the unchanged 15-minute net-delta signal and the same 90% coverage floor. Report ordinary, single-control, and two-control partial Spearman for every day; do not select a subset after viewing results.

The purpose is to determine how frequently the two-control residual changes sign relative to the ordinary hedge association and whether Aug 6 is unusual in control sensitivity. This is post-hoc mechanism research, not new validation evidence.

No paid market-data request is authorized or required.