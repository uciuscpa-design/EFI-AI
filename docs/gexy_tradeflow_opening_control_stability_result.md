# GEXY eight-day opening 15-minute control-stability audit result

## Status

This document records the pre-frozen, local-only post-hoc control-stability audit across all eight existing opening-window GEXY sessions. It is mechanism research, not new out-of-sample validation, and it does not change the historical batch-3 verdict.

Dates:

1. 2026-08-04
2. 2026-08-05
3. 2026-08-06
4. 2026-08-07
5. 2026-08-10
6. 2026-08-11
7. 2026-08-12
8. 2026-08-13

Frozen scope:

- opening 09:30-10:00 America/New_York only
- horizon: 15 minutes only
- signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- momentum control: `backward_return_1m_bps`
- raw-flow control: `flow_net_signed_contracts`
- minimum classified-volume Greek coverage: 90%
- unchanged M+1 causal alignment

## Day-by-day results

| Trading day | n | Ordinary hedge/target | Hedge | momentum | Hedge | raw | Hedge | momentum + raw | Hedge/raw | Hedge/momentum | Raw/momentum | Ordinary-to-both sign flip |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-04 | 29 | -0.418719 | -0.299606 | -0.540576 | -0.436355 | +0.307389 | +0.681281 | +0.126108 | no |
| 2026-08-05 | 29 | -0.486700 | -0.449748 | -0.556839 | -0.522197 | +0.126601 | +0.248276 | +0.130049 | no |
| 2026-08-06 | 29 | -0.209360 | -0.151591 | -0.031445 | +0.121166 | +0.358128 | +0.367980 | -0.125123 | **yes** |
| 2026-08-07 | 29 | -0.356650 | -0.290032 | -0.093923 | -0.118163 | +0.474384 | +0.503941 | +0.408867 | no |
| 2026-08-10 | 29 | -0.090640 | -0.077407 | -0.438253 | -0.415499 | +0.516876 | +0.306897 | +0.191426 | no |
| 2026-08-11 | 29 | -0.063547 | -0.025329 | -0.218745 | -0.114670 | +0.318719 | +0.587192 | +0.320690 | no |
| 2026-08-12 | 29 | -0.401970 | -0.403642 | -0.402376 | -0.403520 | +0.232295 | +0.260099 | +0.521739 | no |
| 2026-08-13 | 29 | -0.144335 | -0.148258 | -0.147564 | -0.146997 | +0.005419 | +0.050739 | -0.325616 | no |

## Eight-day summary

- ordinary hedge association negative: **8 / 8 days (100%)**
- ordinary median: **-0.283005**
- momentum-only partial negative: **8 / 8 days (100%)**
- momentum-only median: **-0.220811**
- raw-only partial negative: **8 / 8 days (100%)**
- raw-only median: **-0.310560**
- frozen momentum+raw partial negative: **7 / 8 days (87.5%)**
- momentum+raw median: **-0.275258**
- ordinary-to-two-control sign-flip days: **1 / 8**
- sign-flip date: **2026-08-06 only**

## Interpretation

The audit satisfies the protocol condition for a rare, concentrated control-sensitive exception. The underlying opening 15-minute `hedge_delta_units` association is negative on all eight existing sessions. It remains negative on every session when controlling momentum alone and on every session when controlling raw signed contracts alone.

Only the joint two-control residual specification changes sign, and only on 2026-08-06. Therefore Aug 6 is best described as an unusual **joint-residualization-sensitive session**, not a day on which the ordinary hedge-flow association itself reversed sign.

This does not erase the batch-3 failure. Batch 3 remains partial replication because its frozen primary endpoint was the two-control residual and that endpoint was positive on Aug 6. The failed day must remain in the historical validation record.

At the same time, the eight-day ordinary 8/8 negative pattern is a scientifically important post-hoc candidate. Because it was identified after examining all existing sessions, it cannot be promoted to a validated endpoint or production rule without a new untouched validation set.

The result also argues against immediately changing the hedge sign convention, aggressor classifier, horizon, strike band, coverage floor, or time window. The instability is localized to the joint residualization architecture rather than the market-flow sign itself.

## Scientific consequence

Current evidence supports three distinct statements:

1. The historical frozen two-control endpoint is **not universal**; batch 3 remains partial replication.
2. The ordinary opening 15-minute hedge-flow association is **sign-stable on all eight existing sessions**, but this is post-hoc evidence only.
3. Joint residualization by momentum plus raw signed contracts can alter the sign in at least one otherwise negative session, so control architecture must be treated as a modeling choice rather than assumed ground truth.

No causal dealer-hedging claim or production trading-edge claim is established.

## Next rule

Do not purchase additional TCBBO until a new untouched validation protocol is frozen. Before defining that protocol, inventory the remaining cached replay/chain dates that have never had TCBBO trade-flow inspected.

Any future validation should preserve the historical two-control endpoint for continuity while separately pre-specifying the ordinary opening 15-minute hedge association as a new candidate robustness endpoint. The ordinary endpoint must not retroactively replace the batch-3 primary result.
