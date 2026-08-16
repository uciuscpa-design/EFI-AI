# GEXY cumulative opening heterogeneity characterization protocol

## Status and purpose

This protocol is frozen after the 17-day 09:40 session-state development screen returned **SELECTED CANDIDATE: NONE**, and before any cumulative leave-one-minute-out characterization is run across the full already-seen development set.

This is not a new predictor search. It does not add features, change the endpoint, inspect reserved holdout dates, or attempt to rescue the failed session-state screen.

The purpose is to answer one descriptive question:

> Across all 17 already-seen opening sessions, how often is the ordinary 15-minute hedge/return association broad within the session versus sign-fragile to a single-minute deletion?

## Frozen dates

Use exactly the same 17 already-seen development dates, in the same order:

1. 2026-08-13
2. 2026-08-12
3. 2026-08-11
4. 2026-08-10
5. 2026-08-07
6. 2026-08-06
7. 2026-08-05
8. 2026-08-04
9. 2026-08-03
10. 2026-07-31
11. 2026-07-30
12. 2026-07-29
13. 2026-07-28
14. 2026-07-27
15. 2026-07-24
16. 2026-07-23
17. 2026-07-22

Do not remove or substitute any date based on sign, magnitude, influence, or prior narrative.

## Reserved holdout remains excluded

Do not read, price, acquire, or otherwise inspect:

- 2026-07-21
- 2026-07-20
- 2026-07-17

Those dates remain untouched and are not needed for this characterization.

## Frozen sample and endpoint

For every development day use exactly:

- opening window 09:30-10:00 America/New_York
- 15-minute horizon only
- 90% classified-volume Greek coverage floor
- same `matched_with_coverage` complete causal sample
- ordinary Endpoint B: Spearman(`hedge_delta_units`, `forward_return_15m_bps`)

For context also reproduce the historical two-control partial Spearman using:

- `backward_return_1m_bps`
- `flow_net_signed_contracts`

No alternate horizon, window, coverage floor, signal, call/put split, state variable, or threshold search is permitted.

## Frozen diagnostic math

Reuse the already-frozen Batch-4/5/6 heterogeneity audit core without changing its mathematics.

For each day report:

1. full-sample ordinary Endpoint-B Spearman;
2. full-sample two-control partial Spearman;
3. 29 leave-one-minute-out ordinary estimates;
4. 29 leave-one-minute-out controlled estimates;
5. negative count/pct, median, min, max, maximum absolute change, and whether any one deletion crosses the full-sample sign;
6. ordinary and controlled rank-product contribution concentration: largest, top-three, top-five absolute contribution shares;
7. rank R² of hedge and target from the two controls.

No observation may be removed from an official endpoint.

## Pre-specified stability categories

Classify the **ordinary Endpoint B** only for descriptive summary using the following frozen categories:

- **strict sign-stable positive:** full-sample Endpoint B > 0 and every finite ordinary leave-one-out estimate > 0;
- **strict sign-stable negative:** full-sample Endpoint B < 0 and every finite ordinary leave-one-out estimate < 0;
- **sign-fragile:** neither strict category applies, including any leave-one-out sign crossing or a full-sample exact zero.

These are descriptive influence categories, not market regimes and not predictive labels.

Also report a secondary `>=80% same-sign` count, but do not use that looser threshold to relabel a strict-category failure.

## Frozen aggregate summary

Across the 17 days report:

- full-sample negative / positive / exact-zero day counts;
- strict sign-stable negative count;
- strict sign-stable positive count;
- sign-fragile count;
- >=80% same-sign ordinary LOO count;
- median, minimum, maximum, standard deviation, Q1, Q3, and IQR of the 17 full-sample ordinary Endpoint-B values;
- median largest-single, top-three, and top-five ordinary contribution shares.

These summaries characterize observed heterogeneity and influence concentration only. They do not establish statistical significance or a deployable state model.

## Interpretation rule

- If both strict sign-stable positive and strict sign-stable negative sessions occur repeatedly, record that broad opposite-sign sessions recur across the cumulative already-seen sample.
- If most opposite-sign days are sign-fragile, weaken the broad-state interpretation accordingly.
- If one sign is mostly strict-stable and the other mostly fragile, record that asymmetry without turning it into a predictor.

Do not create a classifier or threshold from these categories.

## Cost and execution rule

This characterization is strictly **local-only / $0** and reads only existing development feature files. It must make no market-data request.

No reserved holdout purchase or inspection is authorized by this protocol.

## Implementation checkpoint

The protocol was implemented only after all rules above were frozen.

Dedicated characterization script:

- `scripts/gexy_tradeflow_cumulative_heterogeneity_characterization.py`
- implementation commit: `1d46cc90c98f5ff8b424b8745214f427f26bd3e1`

Safeguards:

- `tests/test_gexy_tradeflow_cumulative_heterogeneity_characterization.py`
- safeguard commit: `7ffd04bbe5757917c7b14e1a20e1f35c74616b90`

The script hard-codes the same 17 seen dates and three excluded holdout dates, reuses `audit_day` and the same frozen opening sample, computes exact ordinary leave-one-minute-out values only to assign the pre-specified stability categories, and produces Batch-independent cumulative CSV outputs. It contains no market-data client and no predictor-selection logic.

## Scientific limits

The 17 dates are already-seen development data. This exercise is descriptive, not out-of-sample validation.

Minute-level observations include overlapping 15-minute forward-return labels, so leave-one-minute-out stability is an influence diagnostic rather than an independence-based statistical test.

`hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy. OPRA does not identify dealer inventory or executed underlying hedges. Correlation and influence stability do not establish causality or production edge.
