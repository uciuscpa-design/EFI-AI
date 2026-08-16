# GEXY Batch 5 opening heterogeneity audit protocol

## Status and purpose

This post-validation diagnostic protocol is frozen after the official Batch-5 validation result was revealed and permanently recorded, and before any additional Batch-5 influence or heterogeneity diagnostic is run.

The official Batch-5 verdict is already fixed and cannot be changed by this audit:

- 2026-07-29: Endpoint A `+0.024628`; Endpoint B ordinary `+0.000985`
- 2026-07-28: Endpoint A `+0.298508`; Endpoint B ordinary `+0.130542`
- 2026-07-27: Endpoint A `-0.117435`; Endpoint B ordinary `-0.194581`
- Endpoint A: 1/3 negative, median `+0.024628`
- Endpoint B: 1/3 negative, median `+0.000985`

The frozen Batch-5 interpretation is that Endpoint A remains mixed/mostly positive and the historical two-control architecture is further weakened, while Endpoint B being negative on only 1/3 days materially weakens the idea that a negative ordinary opening-15m association is the dominant sign in nearby sessions.

This audit is diagnostic only. It cannot rescue either endpoint, define a new signal, or create a regime filter.

## Frozen questions

The audit asks only:

1. Is the substantive 2026-07-28 positive ordinary hedge/15m-return association broad across the frozen 29 observations or concentrated in one/few influential minutes?
2. Is the essentially zero 2026-07-29 ordinary association intrinsically sign-fragile under single-observation deletion, as expected for a near-zero sample relationship?
3. Does 2026-07-27 remain a broad negative reference session under the same influence diagnostics?
4. How strongly do the same two frozen controls explain ranked hedge signal and ranked target variation on each Batch-5 day?

No other question may be added after seeing diagnostic results.

## Frozen sample and variables

Use exactly the existing Batch-5 local feature files, in frozen order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

Use exactly:

- opening window 09:30-10:00 America/New_York
- horizon 15 minutes only
- minimum classified-volume Greek coverage 90%
- replay-matched rows through the existing `matched_with_coverage` path
- the same complete-case sample used by the frozen Batch-5 validator

Use only these variables:

- hedge signal: `hedge_delta_units`
- raw-flow control: `flow_net_signed_contracts`
- momentum control: `backward_return_1m_bps`
- target: `forward_return_15m_bps`

No alternate horizon, close window, call/put decomposition, coverage floor, strike split, volatility split, volume split, Greek field, aggressor rule, or market-state variable is permitted.

## Frozen diagnostics

For context, reproduce on the same complete-case sample:

- ordinary hedge/target Spearman
- hedge partial Spearman controlling momentum only
- hedge partial Spearman controlling raw only
- hedge partial Spearman controlling both momentum and raw
- hedge/raw Spearman
- hedge/momentum Spearman
- raw/momentum Spearman

Then compute only the same three diagnostic families already frozen for the Batch-4 heterogeneity audit.

### A. Rank variance removed by controls

On rank-transformed complete cases, fit OLS with an intercept:

- ranked hedge ~ ranked momentum + ranked raw
- ranked target ~ ranked momentum + ranked raw

Report `R^2` and residual standard deviation for each fit. These are statistical decomposition diagnostics only and do not prove causality or classical multicollinearity.

### B. Leave-one-minute-out stability

For each of the 29 complete observations, delete exactly one observation and recompute:

- ordinary hedge/target Spearman
- two-control partial Spearman

For each endpoint/day report:

- number of leave-one-out estimates
- negative count and percentage
- median
- minimum
- maximum
- maximum absolute change from the full-sample estimate
- whether any single deletion changes the full-sample sign

No observation may be permanently removed from an official endpoint.

### C. Rank-product contribution concentration

For the ordinary endpoint, standardize centered hedge and target ranks and compute the per-observation product contribution.

For the controlled endpoint, residualize hedge ranks and target ranks on the two ranked controls, standardize residuals, and compute residual-product contribution.

For each endpoint/day report:

- largest single absolute-contribution share
- top-three absolute-contribution share
- top-five absolute-contribution share
- timestamp of the largest absolute contribution
- sign of that contribution

These diagnostics describe influence concentration only. They do not justify deleting observations.

## Pre-specified interpretation

### 2026-07-28

- If the ordinary result remains positive under all or nearly all leave-one-out deletions and contribution concentration is not dominated by one/few observations, treat the positive session as broad within this small sample. This would strengthen the session-heterogeneity interpretation and reinforce that positive opening sessions can recur outside 2026-07-31.
- If the ordinary result frequently changes sign or is dominated by a very small number of contributions, treat the positive result as influence-sensitive while retaining the official positive Batch-5 endpoint exactly as observed.

### 2026-07-29

- Because the full ordinary result is essentially zero (`+0.000985`), leave-one-out estimates spanning both signs should be interpreted as expected near-zero sign fragility, not as evidence for either direction.
- If all or nearly all leave-one-out estimates unexpectedly remain on one sign, report that stability descriptively, but do not relabel the official near-zero endpoint or promote a directional claim.

### 2026-07-27

- If ordinary estimates remain negative under all or nearly all leave-one-out deletions with non-extreme contribution concentration, treat the negative result as broad within this small sample.
- If sign changes are frequent, treat the negative session as influence-sensitive.

For controlled results, the same stability language may be used, but the failed/mixed historical Endpoint-A verdict remains unchanged.

High control `R^2` or moderate/high pairwise correlations may support a residualization-sensitivity description, but the audit must not claim proven classical multicollinearity or market mechanism without a separately justified test.

## Scientific limits

The official Batch-5 result remains fixed regardless of this audit. No row may be deleted, relabeled, or used to recompute the official Batch-5 endpoint values. No new regime classifier may be selected from these three days.

`hedge_delta_units` remains a liquidity-provider/dealer-hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify dealer inventory or executed underlying hedge trades. Correlation, residualization, influence diagnostics, and sign stability do not establish causality or a production edge.

## Cost rule

This audit is strictly local-only and must make no market-data request. No new Databento purchase is authorized by this protocol.
