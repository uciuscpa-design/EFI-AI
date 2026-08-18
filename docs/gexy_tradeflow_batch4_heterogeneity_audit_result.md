# GEXY Batch 4 opening heterogeneity audit result

## Status

This document records the frozen post-validation heterogeneity audit run after the Batch 4 validation result had already been revealed and recorded. The audit used only the three existing Batch 4 opening samples, the 15-minute horizon, the 90% classified-volume Greek coverage floor, and the four pre-specified variables `hedge_delta_units`, `flow_net_signed_contracts`, `backward_return_1m_bps`, and `forward_return_15m_bps`.

The official Batch 4 validation verdict is unchanged by this audit.

Dates, in frozen order:

1. 2026-08-03
2. 2026-07-31
3. 2026-07-30

No paid data request was made and no observation was removed from an official endpoint.

## Control / residualization context

| Trading day | n | Ordinary Spearman | Partial \| momentum | Partial \| raw | Partial \| both | Hedge/raw | Hedge/momentum | Raw/momentum | Hedge-rank R² from both controls | Target-rank R² from both controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-03 | 29 | -0.136453 | +0.031679 | -0.127053 | +0.107961 | +0.273399 | +0.561576 | -0.221675 | 0.481863 | 0.097032 |
| 2026-07-31 | 29 | +0.272906 | +0.346026 | +0.299584 | +0.372243 | +0.149754 | +0.219704 | +0.038424 | 0.068269 | 0.077180 |
| 2026-07-30 | 29 | -0.145813 | -0.030407 | -0.186960 | -0.023649 | -0.128079 | +0.733990 | -0.198030 | 0.539052 | 0.118851 |

Rank residual standard deviations after both controls were 6.022423 / 7.950332 for hedge/target on 2026-08-03, 8.075964 / 8.037250 on 2026-07-31, and 5.680348 / 7.853690 on 2026-07-30.

The controls explain substantially more ranked hedge variation on 2026-08-03 and 2026-07-30 than on 2026-07-31. This supports describing 2026-08-03 as control-sensitive residualization, but it does not prove classical multicollinearity or a market mechanism.

## Leave-one-minute-out stability

### Ordinary endpoint

| Trading day | LOO estimates | Negative | Negative % | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-03 | 29 | 29 | 100.0% | -0.128626 | -0.258894 | -0.071155 | 0.122441 | no |
| 2026-07-31 | 29 | 0 | 0.0% | +0.275315 | +0.195950 | +0.360153 | 0.087247 | no |
| 2026-07-30 | 29 | 29 | 100.0% | -0.140120 | -0.209633 | -0.050903 | 0.094910 | no |

### Two-control endpoint

| Trading day | LOO estimates | Negative | Negative % | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-08-03 | 29 | 1 | 3.45% | +0.108009 | -0.023570 | +0.171512 | 0.131530 | yes |
| 2026-07-31 | 29 | 0 | 0.0% | +0.369537 | +0.313358 | +0.458681 | 0.086438 | no |
| 2026-07-30 | 29 | 21 | 72.41% | -0.029649 | -0.117662 | +0.055417 | 0.094013 | yes |

## Rank-product contribution concentration

| Trading day | Ordinary largest | Ordinary top 3 | Ordinary top 5 | Ordinary largest timestamp | Ordinary sign | Controlled largest | Controlled top 3 | Controlled top 5 | Controlled largest timestamp | Controlled sign |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---:|
| 2026-08-03 | 11.08% | 29.95% | 45.53% | 2026-08-03 14:00:00+00:00 | +1 | 16.48% | 39.85% | 55.65% | 2026-08-03 14:00:00+00:00 | +1 |
| 2026-07-31 | 10.41% | 29.00% | 44.30% | 2026-07-31 13:46:00+00:00 | +1 | 11.40% | 29.98% | 45.00% | 2026-07-31 13:46:00+00:00 | +1 |
| 2026-07-30 | 13.19% | 30.82% | 42.19% | 2026-07-30 14:00:00+00:00 | -1 | 10.87% | 29.62% | 44.35% | 2026-07-30 13:41:00+00:00 | +1 |

No day is dominated by a single observation under these contribution-share diagnostics. The July 31 result in particular is not explained by one extreme minute: the largest ordinary contribution carries only about 10.4% of total absolute contribution and every leave-one-out ordinary estimate remains positive.

## Frozen interpretation

### 2026-07-31 — broad ordinary sign reversal

The frozen protocol stated that if the July 31 ordinary result remained positive under all leave-one-out deletions and contribution concentration was not extreme, the ordinary sign reversal should be treated as broad within this small opening sample.

That condition is satisfied:

- full-sample ordinary Spearman: +0.272906
- all 29 leave-one-out ordinary estimates remain positive
- leave-one-out range: +0.195950 to +0.360153
- largest absolute ordinary contribution share: 10.41%
- top-three absolute contribution share: 29.00%

Therefore July 31 should be treated as a genuine within-sample positive reversal rather than a one-minute artifact. This strengthens the session-heterogeneity interpretation and materially argues against a universal negative opening association.

### 2026-08-03 — stable ordinary negative, fragile controlled positive

The ordinary negative association is robust to every single deletion:

- full-sample ordinary Spearman: -0.136453
- 29/29 leave-one-out ordinary estimates remain negative
- leave-one-out ordinary range: -0.258894 to -0.071155

The joint two-control positive residual is much less stable:

- full-sample two-control partial: +0.107961
- 28/29 leave-one-out controlled estimates are positive and 1/29 is negative
- controlled range: -0.023570 to +0.171512
- at least one single deletion changes the sign

The controls explain 48.19% of ranked hedge variation but only 9.70% of ranked target variation on this day. The result is therefore best described as a control-sensitive residualization feature that is mostly positive under leave-one-out but not sign-robust to every observation. It should not be promoted to a stable mechanism or used to rescue Endpoint A.

### 2026-07-30 — stable ordinary negative, near-zero controlled residual

The ordinary negative association is stable under all leave-one-out deletions. The two-control residual is near zero and sign-fragile: 21/29 leave-one-out estimates are negative while 8/29 are positive. This supports treating Endpoint A on July 30 as weak/near-zero rather than a robust negative controlled relationship.

## Research conclusion

The audit sharpens, but does not reverse, the Batch 4 conclusion:

1. **July 31 is strong evidence of genuine session heterogeneity.** Its positive ordinary association is broad across the 29-observation opening sample, survives every single-observation deletion, and is not concentrated in one or a few minutes under the frozen contribution metric.
2. **The ordinary negative association on Aug 3 and Jul 30 is substantially more sign-stable than the two-control residual.** Both ordinary endpoints remain negative under all 29 leave-one-out deletions.
3. **The historical two-control endpoint is structurally fragile in Batch 4.** Aug 3 can change sign after one deletion, and Jul 30 is close enough to zero that eight leave-one-out deletions make it positive.
4. The evidence does not justify replacing Endpoint A retroactively, declaring Endpoint B validated, or defining a production rule. The correct research statement remains that the opening 15-minute hedge/return relationship is conditional and heterogeneous across sessions.

No causal dealer-hedging claim is established. `hedge_delta_units` remains a liquidity-provider hedge proxy, and OPRA does not identify dealer inventory or executed hedge trades.

## Next rule

Do not tune the existing signal or mine the Batch 4 dates for a new regime classifier.

Before buying more TCBBO, freeze any next untouched validation protocol separately. A defensible next batch may preserve Endpoint A for historical continuity while treating ordinary 15-minute association as a robustness endpoint, but the protocol must explicitly acknowledge the July 31 broad positive reversal and must not assume the ordinary sign is universally negative.
