# GEXY eight-day opening control-stability audit protocol

## Status

This is a **post-hoc local-only mechanism diagnostic** using all existing GEXY TCBBO sessions. It is not a new validation set and must not change the historical batch-3 verdict.

The batch-3 primary opening 15-minute endpoint was negative on 2026-08-05 and 2026-08-04 but positive on 2026-08-06 after controlling momentum and raw signed contracts. A pre-frozen control-structure audit then showed that 2026-08-06 was negative ordinarily and under either single control, but changed sign only when both controls were used simultaneously.

## Frozen question

Across **all eight existing opening-window sessions**, how stable is the control structure of the unchanged 15-minute net-delta relationship?

Use exactly these dates:

1. 2026-08-04
2. 2026-08-05
3. 2026-08-06
4. 2026-08-07
5. 2026-08-10
6. 2026-08-11
7. 2026-08-12
8. 2026-08-13

For the five earlier research sessions, restrict the already generated two-window feature files to the original **09:30-10:00 America/New_York flow-minute window**. For batch-3 dates, the generated files already contain opening only. Do not use closing rows.

## Frozen endpoint

Use exactly:

- horizon: **15 minutes only**
- hedge signal: `hedge_delta_units`
- target: `forward_return_15m_bps`
- momentum control: `backward_return_1m_bps`
- raw-flow control: `flow_net_signed_contracts`
- minimum classified-volume Greek coverage: **90%**
- same M+1 causal alignment

Do not select call/put components, other horizons, other windows, different coverage floors, or different controls in this audit.

## Required day-level reporting

For each of the eight dates report:

1. observations
2. ordinary hedge-vs-target Spearman
3. hedge partial Spearman controlling momentum only
4. hedge partial Spearman controlling raw flow only
5. hedge partial Spearman controlling momentum + raw flow
6. hedge-vs-raw Spearman
7. hedge-vs-momentum Spearman
8. raw-vs-momentum Spearman
9. whether ordinary and two-control signs differ

## Required summary

Across all eight dates report:

- negative-day count for ordinary hedge association
- negative-day count for momentum-only partial
- negative-day count for raw-only partial
- negative-day count for the frozen two-control partial
- count and identity of ordinary-to-two-control sign-flip days
- median value for each of the four hedge/target specifications

## Interpretation rule

- If sign flips are rare and concentrated on 2026-08-06, treat Aug 6 as an unusual control-sensitive session rather than redefining the endpoint.
- If sign flips are common, conclude that the frozen residual endpoint is broadly control-structure sensitive and should not be treated as a stable mechanism without a stronger model of raw-flow/momentum interactions.
- If ordinary and both single-control specifications are broadly negative while the two-control endpoint is substantially less stable, focus future research on the joint residualization structure rather than tuning the market signal.

No observation may be removed because it is unfavorable. This analysis cannot upgrade the research or batch-3 sessions to new out-of-sample evidence.

No paid market-data request is authorized or required.