# GEXY batch-3 control-structure audit protocol

## Status

This is a local-only post-validation statistical diagnostic. It is not a new out-of-sample test and must not be used to remove, relabel, or replace the failed 2026-08-06 batch-3 result.

Batch 3 found the frozen opening 15-minute endpoint negative on 2026-08-05 and 2026-08-04 but positive on 2026-08-06 after controlling for momentum and raw flow. Subsequent quality checks found comparable replay matching and Greek coverage across all three dates, so the next question is whether the Aug 6 sign reversal is associated with control structure rather than missing/poor data.

## Frozen question

For the unchanged opening-window net-delta endpoint, how does the hedge/forward-return association change as controls are added, and how strongly are the signal and controls rank-correlated with one another?

Use exactly the three batch-3 dates:

1. 2026-08-06
2. 2026-08-05
3. 2026-08-04

Use exactly:

- opening 09:30-10:00 America/New_York files already generated
- 90% classified-volume Greek coverage floor
- horizons 5 and 15 minutes
- hedge signal: `hedge_delta_units`
- raw control: `flow_net_signed_contracts`
- momentum control: `backward_return_1m_bps`
- unchanged forward-return targets

## Required reporting

For each date and horizon report on the same filtered observations:

1. ordinary Spearman: hedge signal vs target
2. ordinary Spearman: raw flow vs target
3. ordinary Spearman: momentum vs target
4. Spearman: hedge signal vs raw flow
5. Spearman: hedge signal vs momentum
6. Spearman: raw flow vs momentum
7. partial Spearman: hedge vs target controlling momentum only
8. partial Spearman: hedge vs target controlling raw flow only
9. partial Spearman: hedge vs target controlling both momentum and raw flow
10. whether adding both controls changes the sign relative to the ordinary hedge association

## Interpretation rule

- If Aug 6 is already positive before controls, treat the failure as ordinary signal heterogeneity.
- If Aug 6 is negative ordinarily and under each single control but becomes positive only under both controls, flag a possible multivariable suppression/collinearity effect.
- If controlling raw flow alone produces the sign reversal, focus on the relation between raw option flow and Greek-weighted flow rather than inventing a new market regime.
- If controlling momentum alone produces the sign reversal, focus on reactive price-move structure.
- Do not alter the frozen batch-3 verdict regardless of this diagnostic.
- Do not select call/put components, another horizon, a new coverage threshold, or a new time sub-window during this audit.

No paid market-data request is authorized or required.