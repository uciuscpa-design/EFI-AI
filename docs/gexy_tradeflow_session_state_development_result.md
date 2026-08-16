# GEXY opening session-state development result

## Status

This document records the completed development-only early-opening session-state screen under the frozen protocol. The screen used only the 17 already-seen development dates, the frozen 09:40 America/New_York causal cutoff, the six pre-specified univariate descriptors, and the continuous ordinary opening-15m Endpoint-B Spearman target.

The reserved untouched holdout block remained unread and unpurchased:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

The screen made no market-data request.

## Development dates

The exact development set remained:

2026-08-13, 2026-08-12, 2026-08-11, 2026-08-10, 2026-08-07, 2026-08-06, 2026-08-05, 2026-08-04, 2026-08-03, 2026-07-31, 2026-07-30, 2026-07-29, 2026-07-28, 2026-07-27, 2026-07-24, 2026-07-23, 2026-07-22.

Every descriptor had finite values for all 17 days.

## Frozen selection rule

A descriptor was eligible to advance only if all of the following held:

1. at least 15 finite development day pairs;
2. absolute full-sample Spearman correlation with Endpoint B at least 0.35;
3. at least 80% leave-one-day-out sign consistency;
4. no one-day deletion reversed the full-sample sign when at least 16 finite LOO estimates existed.

At most one candidate could advance. No threshold, feature, cutoff, or combination was allowed to change after the screen.

## Screen results

| Descriptor | Finite day pairs | Spearman vs Endpoint B | Abs Spearman | LOO sign consistency | LOO range | Any opposite sign? | Eligible |
|---|---:|---:|---:|---:|---:|---|---|
| `early_forward_return_bps` | 17 | -0.112745 | 0.112745 | 15/17 = 88.24% | -0.291176 to +0.023529 | yes | no |
| `early_hedge_delta_imbalance` | 17 | +0.022059 | 0.022059 | 11/17 = 64.71% | -0.105882 to +0.167647 | yes | no |
| `early_raw_contract_imbalance` | 17 | -0.144608 | 0.144608 | 15/17 = 88.24% | -0.282353 to +0.026471 | yes | no |
| `early_hedge_gex_imbalance` | 17 | +0.071078 | 0.071078 | 14/17 = 82.35% | -0.114706 to +0.191176 | yes | no |
| `early_classified_contract_volume` | 17 | +0.068627 | 0.068627 | 14/17 = 82.35% | -0.091176 to +0.158824 | yes | no |
| `early_gross_abs_delta_notional` | 17 | -0.188725 | 0.188725 | 17/17 = 100.00% | -0.332353 to -0.038235 | no | no |

The strongest absolute development correlation was `early_gross_abs_delta_notional` at **-0.188725**. Its leave-one-day-out sign was unusually stable (17/17 negative), but its effect size remained far below the frozen |Spearman| >= 0.35 eligibility threshold.

No other descriptor approached the frozen effect-size threshold, and several were sign-fragile under one-day deletion.

## Frozen adjudication

**SELECTED CANDIDATE: NONE.**

This is the required outcome under the frozen rule. The 09:40 six-descriptor univariate screen did not identify a sufficiently strong and robust early-opening descriptor for the later day-level Endpoint-B association.

The correct action is therefore:

- do not lower the 0.35 threshold;
- do not change the 09:40 cutoff;
- do not add or combine descriptors under this protocol;
- do not purchase or inspect the reserved 2026-07-21 / 2026-07-20 / 2026-07-17 holdout block for this failed screen.

## Interpretation

The negative result is informative. The already-established cross-session heterogeneity in the opening hedge/return relationship is not well explained by any of the six simple early-opening state summaries tested here.

The most stable descriptor, early gross hedge-delta activity, showed only a modest monotonic association with the later session-level Endpoint-B value. That is not sufficient evidence to promote it to untouched validation.

This result does not prove that session heterogeneity is unpredictable. It only rejects this specific pre-specified 09:40 univariate descriptor set as a strong enough development screen under the frozen thresholds.

## Data and execution integrity

A pre-screen wiring error initially prevented `flow_classified_contract_volume` from surviving raw/hedge alignment. The run aborted before any descriptor correlations or candidate selection were produced. The repair attached that already-frozen denominator by exact causal timestamp, added a regression test, and did not change the descriptor set, cutoff, target, thresholds, development dates, or reserved holdout dates.

The corrected safeguard suite passed before the successful screen.

## Scientific limits

This was exploratory development on already-seen dates, not out-of-sample validation. The screen does not establish causality, a market regime mechanism, observed dealer inventory, executed hedge flow, or a production trading edge.

`hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy derived from OPRA trade price versus pre-trade NBBO and Black-76 Greeks.
