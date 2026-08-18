# GEXY Batch 4 opening heterogeneity audit protocol

## Status and purpose

This post-validation diagnostic protocol is frozen after the Batch 4 15-minute endpoints were revealed and recorded, and before any additional Batch 4 heterogeneity diagnostic is run.

The Batch 4 validation verdict is already fixed and cannot be changed by this audit:

- 2026-08-03: Endpoint A (momentum + raw controlled) `+0.107961`; Endpoint B ordinary `-0.136453`
- 2026-07-31: Endpoint A `+0.372243`; Endpoint B ordinary `+0.272906`
- 2026-07-30: Endpoint A `-0.023649`; Endpoint B ordinary `-0.145813`
- Endpoint A: 1/3 negative, median `+0.107961` — failed Batch 4 validation
- Endpoint B: 2/3 negative, median `-0.136453` — partial directional replication only

The audit question is deliberately narrower than signal discovery:

1. Is the 2026-07-31 positive ordinary hedge/return association broad across the 29 frozen observations or concentrated in a small number of influential minutes?
2. Is the 2026-08-03 ordinary-negative / two-control-positive reversal broad under residualization or fragile to a small number of observations?
3. How strongly do the two frozen controls explain the ranked hedge signal and ranked 15-minute target on each Batch 4 day?

This audit does not rescue either Batch 4 endpoint and does not define a new trading rule.

## Frozen sample and variables

Use exactly the existing Batch 4 local feature files for, in this order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

Use exactly:

- opening window 09:30-10:00 America/New_York
- horizon 15 minutes only
- minimum classified-volume Greek coverage 90%
- replay-matched rows only through the existing `matched_with_coverage` path
- the same complete-case sample used by the frozen Batch 4 validator

Use only these four statistical variables:

- hedge signal: `hedge_delta_units`
- raw-flow control: `flow_net_signed_contracts`
- momentum control: `backward_return_1m_bps`
- target: `forward_return_15m_bps`

No call/put decomposition, alternate horizon, alternate time window, alternate Greek field, volume split, volatility split, strike split, or new market-state feature is permitted.

## Frozen diagnostics

For every day report the already-defined associations for context:

- ordinary hedge/target Spearman
- hedge partial Spearman controlling momentum only
- hedge partial Spearman controlling raw only
- hedge partial Spearman controlling both momentum and raw
- hedge/raw, hedge/momentum, and raw/momentum Spearman

Then compute only the following new diagnostics on rank-transformed complete cases.

### A. Rank variance removed by controls

Fit ordinary least squares on ranks with an intercept, for diagnostic decomposition only:

- ranked hedge ~ ranked momentum + ranked raw
- ranked target ~ ranked momentum + ranked raw

Report `R^2` for both fits and residual standard deviations. These measure how much ranked hedge/target variation the fixed controls remove; they do not establish causality or multicollinearity.

### B. Leave-one-minute-out stability

For each of the 29 complete observations, recompute:

- ordinary hedge/target Spearman after omitting that one observation
- two-control partial Spearman after omitting that one observation

Report for each endpoint:

- number of leave-one-out estimates
- negative estimate count and percentage
- median
- minimum
- maximum
- maximum absolute change from the full-sample estimate
- whether any single deletion changes the sign of the full-sample estimate

This is an influence/stability diagnostic only. It is not a method for selecting or deleting minutes.

### C. Rank-product contribution concentration

For the ordinary endpoint, center standardized hedge and target ranks and compute the per-observation product contribution.

For the two-control endpoint, residualize hedge ranks and target ranks on the two ranked controls, standardize the residuals, and compute the per-observation residual-product contribution.

For each endpoint report:

- share of total absolute contribution carried by the single largest absolute contribution
- share carried by the three largest absolute contributions
- share carried by the five largest absolute contributions
- timestamp of the single largest absolute contribution
- sign of that contribution

These concentration diagnostics describe whether an observed correlation is diffuse or dominated by a few observations. They do not justify deleting those observations.

## Pre-specified interpretation

- **2026-07-31 ordinary result remains positive under all leave-one-out deletions and contribution concentration is not extreme:** treat the ordinary sign reversal as broad within this small opening sample, strengthening the heterogeneity interpretation.
- **2026-07-31 ordinary sign frequently flips under leave-one-out or is dominated by one/few contributions:** treat the reversal as fragile/influence-sensitive, while retaining the failed Batch 4 day exactly as observed.
- **2026-08-03 two-control result remains positive under all/most leave-one-out deletions while ordinary remains negative:** treat the control-induced sign reversal as a reproducible residualization feature of that day's sample, not a one-minute artifact.
- **2026-08-03 controlled sign frequently changes under leave-one-out:** treat the residual sign flip as fragile.
- High control `R^2` or moderate/high pairwise correlations may support a statistical residualization/suppression explanation, but this audit must not label classical multicollinearity as proven without a separately justified criterion.

2026-07-30 serves only as a same-batch negative reference day.

## Scientific limits

The Batch 4 validation result remains failed/mixed regardless of this audit. No observation may be removed, relabeled, or used to recompute the official Batch 4 endpoints. No new hypothesis may be called validated from this post-result analysis.

`hedge_delta_units` remains a liquidity-provider/dealer hedge proxy inferred from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. OPRA does not identify customer/dealer inventory or executed underlying hedge trades. Statistical residualization and influence diagnostics do not establish market mechanism, causality, or production edge.

## Cost rule

This audit is local-only and must make no market-data request. No new Databento purchase is authorized.

## Frozen implementation checkpoint

The audit was implemented only after this protocol was committed, and before any audit output was viewed:

- `packages/gexy/tradeflow_batch4_heterogeneity.py` — fixed sample construction, rank-control decomposition, leave-one-minute-out calculations, and contribution concentration
- `scripts/gexy_tradeflow_batch4_heterogeneity_audit.py` — local-only CLI fixed to the protocol variables and 15-minute target
- `tests/test_gexy_tradeflow_batch4_heterogeneity.py` — numerical/unit safeguards
- `tests/test_gexy_tradeflow_batch4_heterogeneity_audit_cli.py` — CLI launch/scope safeguard

Implementation does not add any alternate horizon, window, signal, coverage threshold, or market-state feature. The audit result must be recorded before any further Batch 4 exploratory work.