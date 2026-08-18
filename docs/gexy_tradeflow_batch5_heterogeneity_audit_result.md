# GEXY Batch 5 opening heterogeneity audit result

## Status

This document records the frozen post-validation Batch-5 heterogeneity audit run after the official Batch-5 validation result had already been revealed and permanently recorded. The audit used only the existing Batch-5 opening samples, the 15-minute horizon, the 90% classified-volume Greek coverage floor, and the four pre-specified variables `hedge_delta_units`, `flow_net_signed_contracts`, `backward_return_1m_bps`, and `forward_return_15m_bps`.

The official Batch-5 validation verdict is unchanged by this audit.

Dates, in frozen order:

1. 2026-07-29
2. 2026-07-28
3. 2026-07-27

No paid data request was made and no observation was removed from an official endpoint.

## Control / residualization context

| Trading day | n | Ordinary Spearman | Partial \| momentum | Partial \| raw | Partial \| both | Hedge/raw | Hedge/momentum | Raw/momentum | Hedge-rank R² from both controls | Target-rank R² from both controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-07-29 | 29 | +0.000985 | +0.148334 | -0.118244 | +0.024628 | -0.291626 | +0.393596 | +0.083744 | 0.261019 | 0.220283 |
| 2026-07-28 | 29 | +0.130542 | +0.192501 | +0.228585 | +0.298508 | -0.109852 | +0.396059 | -0.037438 | 0.165905 | 0.306106 |
| 2026-07-27 | 29 | -0.194581 | -0.105754 | -0.174180 | -0.117435 | +0.088177 | +0.629064 | +0.136453 | 0.395727 | 0.236065 |

Rank residual standard deviations after both controls were 7.192267 / 7.387840 for hedge/target on 2026-07-29, 7.641115 / 6.969405 on 2026-07-28, and 6.503776 / 7.312690 on 2026-07-27.

## Leave-one-minute-out stability

### Ordinary endpoint

| Trading day | LOO estimates | Negative | Negative % | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-07-29 | 29 | 15 | 51.72% | -0.004379 | -0.062397 | +0.073892 | 0.072906 | yes |
| 2026-07-28 | 29 | 0 | 0.00% | +0.129721 | +0.037767 | +0.217843 | 0.092775 | no |
| 2026-07-27 | 29 | 29 | 100.00% | -0.195950 | -0.297756 | -0.133552 | 0.103175 | no |

### Two-control endpoint

| Trading day | LOO estimates | Negative | Negative % | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-07-29 | 29 | 6 | 20.69% | +0.027336 | -0.070632 | +0.209316 | 0.184688 | yes |
| 2026-07-28 | 29 | 0 | 0.00% | +0.298057 | +0.215541 | +0.381671 | 0.083162 | no |
| 2026-07-27 | 29 | 29 | 100.00% | -0.106314 | -0.315403 | -0.018932 | 0.197968 | no |

## Rank-product contribution concentration

| Trading day | Ordinary largest | Ordinary top 3 | Ordinary top 5 | Ordinary largest timestamp | Ordinary sign | Controlled largest | Controlled top 3 | Controlled top 5 | Controlled largest timestamp | Controlled sign |
|---|---:|---:|---:|---|---:|---:|---:|---:|---|---:|
| 2026-07-29 | 10.82% | 27.67% | 42.12% | 2026-07-29 13:32:00+00:00 | -1 | 14.78% | 34.97% | 49.45% | 2026-07-29 13:33:00+00:00 | -1 |
| 2026-07-28 | 11.70% | 28.75% | 42.51% | 2026-07-28 13:48:00+00:00 | +1 | 16.19% | 32.94% | 47.32% | 2026-07-28 13:48:00+00:00 | +1 |
| 2026-07-27 | 9.32% | 26.48% | 42.56% | 2026-07-27 14:00:00+00:00 | +1 | 17.72% | 38.17% | 48.37% | 2026-07-27 14:00:00+00:00 | +1 |

No ordinary day is dominated by a single observation under the frozen contribution-share diagnostic. The largest ordinary absolute-contribution share is between 9.32% and 11.70% across the three days.

## Frozen interpretation

### 2026-07-28 — broad positive session

The frozen protocol stated that if the July 28 ordinary result remained positive under all or nearly all leave-one-out deletions and contribution concentration was not dominated by one/few observations, the positive session should be treated as broad within this small sample.

That condition is satisfied:

- full-sample ordinary Spearman: +0.130542
- all 29 leave-one-out ordinary estimates remain positive
- leave-one-out ordinary range: +0.037767 to +0.217843
- largest ordinary absolute-contribution share: 11.70%
- top-three ordinary absolute-contribution share: 28.75%

The two-control result is also positive under all 29 leave-one-out deletions, with a range of +0.215541 to +0.381671.

Therefore July 28 is best treated as a broad positive opening session under the frozen construction, not as a one-minute artifact. This provides a second broad positive untouched session after the previously observed 2026-07-31 reversal and strengthens the session-heterogeneity interpretation.

### 2026-07-29 — near-zero and sign-fragile

The full ordinary result is essentially zero at +0.000985. Its leave-one-out estimates span both signs almost evenly:

- 15/29 negative, 14/29 positive
- median -0.004379
- range -0.062397 to +0.073892
- at least one deletion changes the full-sample sign

This exactly matches the pre-specified near-zero fragility interpretation. July 29 should not be assigned a directional sign for research conclusions. The controlled result is also sign-fragile, with 6/29 negative leave-one-out estimates and a range of -0.070632 to +0.209316.

### 2026-07-27 — broad negative session

The frozen protocol stated that if July 27 remained negative under all or nearly all ordinary leave-one-out deletions with non-extreme concentration, it should be treated as broad within this small sample.

That condition is satisfied:

- full-sample ordinary Spearman: -0.194581
- all 29 ordinary leave-one-out estimates remain negative
- leave-one-out ordinary range: -0.297756 to -0.133552
- largest ordinary absolute-contribution share: 9.32%

The two-control endpoint is also negative under all 29 leave-one-out deletions, with a range of -0.315403 to -0.018932.

Therefore July 27 is a broad negative reference session rather than an influence-sensitive one.

## Research conclusion

The Batch-5 heterogeneity audit sharpens the official Batch-5 result without changing it:

1. **2026-07-28 is a broad positive session.** Its positive ordinary association survives every single-observation deletion and is not dominated by one/few observations under the frozen concentration metric.
2. **2026-07-27 is a broad negative session.** Its negative ordinary association also survives every single-observation deletion and is not concentrated in one observation.
3. **2026-07-29 is genuinely near zero and sign-fragile.** It should not be used as evidence for either direction.
4. The two-control endpoint shows the same broad positive/broad negative contrast on July 28 versus July 27, while July 29 remains fragile.
5. Combined with Batch 4, the evidence now directly contains broad positive, broad negative, and near-zero opening sessions under the same construction. That is stronger evidence for session heterogeneity and against a universal or consistently dominant sign.

The result does not identify the source of heterogeneity, justify a regime classifier, establish causality, or imply a production edge. `hedge_delta_units` remains a liquidity-provider hedge proxy; OPRA does not identify dealer inventory or executed underlying hedge trades.

## Next rule

Do not tune a regime classifier on Batches 4-5 and do not alter the signal definition, controls, classifier, sign convention, window, strike band, coverage floor, or 15-minute horizon in response to these diagnostics.

If additional untouched validation is acquired, freeze the dates, endpoints, data scope, and interpretation before pricing or purchase. The next batch should test whether the observed three-state pattern (broad positive, broad negative, near-zero) continues to recur under the unchanged construction rather than assuming a negative directional hypothesis.