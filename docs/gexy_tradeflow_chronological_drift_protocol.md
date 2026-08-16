# GEXY chronological drift characterization protocol

## Status and purpose

This protocol is frozen after the cumulative 17-day heterogeneity characterization showed 12 strict sign-stable negative sessions, 3 strict sign-stable positive sessions, and 2 sign-fragile sessions, and before any chronological-drift calculation is run.

The motivating observation is descriptive and already visible in the cumulative result: strict positive sessions occur in late July while the available August sessions are all negative. Because that observation motivated this protocol, this exercise is explicitly **post-hoc descriptive characterization**, not confirmatory validation and not a predictor search.

The question is:

> Does the already-seen 17-day sample show meaningful chronological nonstationarity in the ordinary opening-15m hedge/return association?

## Frozen data scope

Use exactly the same 17 already-seen sessions and unchanged ordinary Endpoint-B construction. Analyze them in chronological order, oldest to newest:

1. 2026-07-22
2. 2026-07-23
3. 2026-07-24
4. 2026-07-27
5. 2026-07-28
6. 2026-07-29
7. 2026-07-30
8. 2026-07-31
9. 2026-08-03
10. 2026-08-04
11. 2026-08-05
12. 2026-08-06
13. 2026-08-07
14. 2026-08-10
15. 2026-08-11
16. 2026-08-12
17. 2026-08-13

For each day recompute from the existing local feature files:

- opening 09:30-10:00 America/New_York only
- 15-minute horizon only
- 90% classified-volume Greek coverage floor
- ordinary Endpoint B = Spearman(`hedge_delta_units`, `forward_return_15m_bps`)
- strict stability category from the already-frozen cumulative characterization rule

Do not substitute dates or use any reserved holdout date.

## Reserved holdout remains excluded

Do not read, price, acquire, or inspect:

- 2026-07-21
- 2026-07-20
- 2026-07-17

No holdout purchase is authorized by this protocol.

## Frozen diagnostics

### 1. Ordinal-time association

Assign chronological index 1 through 17, oldest to newest, and compute Spearman correlation between chronological index and ordinary Endpoint B.

Also compute 17 leave-one-day-out trend Spearman estimates and report:

- median
- minimum
- maximum
- same-sign count/pct relative to the full-sample trend
- whether any deletion reverses the full-sample trend sign

This is a descriptive monotonic-drift diagnostic only.

### 2. Five-session rolling median

Compute the trailing 5-session median ordinary Endpoint B for every chronological position with five available sessions. Do not optimize the window length; 5 is frozen before execution.

Report the 13 rolling medians and their signs. Do not turn a rolling median into a trading threshold.

### 3. Sign-run structure

Using only the full-sample ordinary Endpoint-B sign (>0 positive, <0 negative, exact zero zero), report:

- number of sign runs
- longest consecutive negative run
- longest consecutive positive run
- terminal run sign and length

Do not attach a p-value or independence claim to the run structure.

### 4. Calendar-month descriptive partition

Because the visible chronology motivating this protocol crosses July/August, report a post-hoc calendar-month summary for July 2026 versus August 2026:

- days
- negative / positive / zero counts
- strict-stable negative / strict-stable positive / fragile counts
- median Endpoint B
- minimum / maximum Endpoint B

This month partition is explicitly motivated after seeing the cumulative table. It is descriptive only and may not be used as a production regime rule or presented as pre-specified evidence.

## Interpretation rule

- A negative ordinal-time correlation with stable leave-one-day-out sign, increasingly negative rolling medians, and a long terminal negative run may be described as **evidence of temporal nonstationarity in this already-seen sample**.
- If the ordinal trend is weak or sign-fragile while month summaries differ, describe the pattern as **calendar-clustered heterogeneity rather than a clean monotonic drift**.
- If neither structure is strong, retain only the broader conclusion that opposite-sign session states recur.

Do not infer a causal market regime, calendar rule, or deployable predictor from any outcome.

## Cost and execution rule

This characterization is strictly **local-only / $0**. It reads only existing local feature files and contains no market-data request.

No new feature search, alternate horizon, alternate window, state descriptor, classifier, or holdout inspection is authorized.

## Implementation checkpoint

The protocol above was frozen before implementation.

Dedicated characterization script:

- `scripts/gexy_tradeflow_chronological_drift.py`
- initial implementation commit: `b44ea248a4ee46952d59cf1342922d8f882cade1`
- direct-script import hardening commit: `8b8cc2bb67cd664c123ed74536b3efd09cfede7c`

Safeguards:

- `tests/test_gexy_tradeflow_chronological_drift.py`
- safeguard commit: `0b6c6514ce35dfb7c3ebff902e8b5ed4842df52b`

Before any local execution, the script-to-script helper import was removed to avoid a Windows direct-execution path dependency. The same already-frozen leave-one-minute-out values and strict sign-stability classification are now implemented locally in the drift script using the existing package-level frozen Spearman function. This technical hardening changed no dates, endpoint values, diagnostics, rolling window, interpretation rule, or data access.

The implementation hard-codes the 17 chronological seen dates and the three excluded holdout dates, recomputes the unchanged 90%-coverage opening Endpoint B from existing local feature files, fixes the rolling window at five sessions, and performs only the diagnostics listed above. It contains no market-data client and no predictor-selection logic.

## Scientific limits

All 17 sessions are already-seen development data. The calendar-month split is explicitly post-hoc. The sample is short and contiguous, so temporal clustering may reflect transient market conditions rather than a persistent mechanism.

`hedge_delta_units` remains an inferred liquidity-provider/dealer-hedge proxy. This characterization does not establish observed dealer inventory, executed hedge flow, causality, statistical stationarity, or production trading edge.
