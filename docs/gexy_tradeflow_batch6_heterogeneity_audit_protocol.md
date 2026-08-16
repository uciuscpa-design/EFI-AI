# GEXY Batch 6 opening heterogeneity audit protocol

## Status and purpose

This post-validation diagnostic protocol is frozen after the official Batch-6 result was revealed and permanently recorded, and before any Batch-6 influence or contribution diagnostic is run.

The official Batch-6 result is fixed and cannot be changed by this audit:

- 2026-07-24: Endpoint A `-0.109626`; Endpoint B ordinary `-0.123645`
- 2026-07-23: Endpoint A `+0.299817`; Endpoint B ordinary `+0.329557`
- 2026-07-22: Endpoint A `-0.120838`; Endpoint B ordinary `-0.230542`
- Endpoint A: 2/3 negative, median `-0.109626`
- Endpoint B: 2/3 negative, 1/3 positive, median `-0.123645`

The frozen Batch-6 interpretation is that mixed Endpoint-B signs directly replicate cross-session heterogeneity under the unchanged construction. This audit is diagnostic only. It cannot rescue a directional hypothesis, redefine either endpoint, remove observations, or create a regime classifier.

## Frozen questions

The audit asks only:

1. Is the 2026-07-23 positive ordinary association broad across the frozen 29 observations or concentrated in one/few influential minutes?
2. Is the 2026-07-24 negative ordinary association broad or influence-sensitive?
3. Is the 2026-07-22 negative ordinary association broad or influence-sensitive?
4. How strongly do the same two frozen controls explain ranked hedge signal and ranked target variation on each Batch-6 day?

No additional question may be added after diagnostic results are visible.

## Frozen sample and variables

Use exactly the existing Batch-6 local feature files, in frozen order:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

Use exactly:

- opening window 09:30-10:00 America/New_York
- horizon 15 minutes only
- minimum classified-volume Greek coverage 90%
- replay-matched rows through the existing `matched_with_coverage` path
- the same complete-case sample used by the frozen Batch-6 validator

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

Then compute only the same three diagnostic families already frozen and used for the Batch-4 and Batch-5 heterogeneity audits.

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

### 2026-07-23

- If the ordinary result remains positive under all or nearly all leave-one-out deletions and contribution concentration is not dominated by one/few observations, treat the positive session as broad within this small sample. This would independently reinforce the prior evidence that broad positive opening sessions recur under the unchanged construction.
- If the ordinary result frequently changes sign or is dominated by very few observations, treat the positive result as influence-sensitive while retaining the official +0.329557 endpoint exactly as observed.

### 2026-07-24 and 2026-07-22

- If ordinary estimates remain negative under all or nearly all leave-one-out deletions with non-extreme contribution concentration, treat each negative result as broad within this small sample.
- If sign changes are frequent, treat that negative session as influence-sensitive while retaining its official endpoint unchanged.

For controlled results, the same stability language may be used, but the historical Endpoint-A architecture remains only a continuity diagnostic and is not revalidated by this audit.

High control `R^2` or moderate/high pairwise correlations may support a residualization-sensitivity description, but the audit must not claim proven classical multicollinearity or market mechanism without a separately justified test.

## Frozen implementation checkpoint

The diagnostic implementation was added only after this protocol was first committed:

- audit CLI: `scripts/gexy_tradeflow_batch6_heterogeneity_audit.py`
- audit CLI commit: `0258947d7a435731ababa0fcc29f7604ccfaca8b`
- CLI/order safeguard: `tests/test_gexy_tradeflow_batch6_heterogeneity_audit_cli.py`
- safeguard commit: `5bf99566561356230bd312b960895922f634b9bd`

The Batch-6 wrapper imports the already-existing `audit_day` implementation from `packages/gexy/tradeflow_batch4_heterogeneity.py`, preserving the same calculations used for the prior Batch-4 and Batch-5 audits. It writes a Batch-6-specific CSV and does not overwrite earlier audit outputs.

No Batch-6 audit result had been run or inspected when this implementation checkpoint was recorded.

## Scientific limits

The official Batch-6 result remains fixed regardless of this audit. No row may be deleted, relabeled, or used to recompute the official Batch-6 endpoint values. No new regime classifier may be selected from these three days.

`hedge_delta_units` remains a liquidity-provider/dealer-hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify dealer inventory or executed underlying hedge trades. Correlation, residualization, influence diagnostics, and sign stability do not establish causality or a production edge.

## Cost rule

This audit is strictly local-only and must make no market-data request. No new Databento purchase is authorized by this protocol.
