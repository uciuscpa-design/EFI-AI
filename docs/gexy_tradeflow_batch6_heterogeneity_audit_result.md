# GEXY Batch 6 opening heterogeneity audit result

## Status

This document records the frozen post-validation Batch-6 heterogeneity audit after the official Batch-6 result was permanently recorded. The audit was specified before execution and cannot change the official Batch-6 endpoint values or verdict.

Frozen dates and order:

1. 2026-07-24
2. 2026-07-23
3. 2026-07-22

Frozen sample and variables remained unchanged:

- opening window 09:30-10:00 America/New_York only
- horizon 15 minutes only
- minimum classified-volume Greek coverage 90%
- same replay-matched complete-case sample as the Batch-6 validator
- `hedge_delta_units`
- `flow_net_signed_contracts`
- `backward_return_1m_bps`
- `forward_return_15m_bps`

The safeguard suite passed 5/5 before the audit. The audit used only existing local feature CSVs and made no market-data request.

## Control / residualization context

| Trading day | N | Ordinary | Partial \| momentum | Partial \| raw | Partial \| both | Hedge/raw | Hedge/momentum | Raw/momentum | Hedge rank R² from controls | Target rank R² from controls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-07-24 | 29 | -0.123645 | -0.048996 | -0.176446 | -0.109626 | +0.288670 | +0.466995 | -0.092611 | 0.329208 | 0.048229 |
| 2026-07-23 | 29 | +0.329557 | +0.352678 | +0.269725 | +0.299817 | -0.319704 | +0.262562 | -0.249754 | 0.137816 | 0.078530 |
| 2026-07-22 | 29 | -0.230542 | -0.089352 | -0.264780 | -0.120838 | +0.165517 | +0.516256 | +0.093596 | 0.280377 | 0.130522 |

The 2026-07-23 positive sign is present in the ordinary association, both single-control partials, and the joint two-control residual. The two negative days likewise retain negative signs throughout the same control views. This is descriptive stability, not proof of mechanism or causality.

## Leave-one-minute-out stability

### Ordinary endpoint

| Trading day | LOO estimates | Negative count | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-07-24 | 29 | 29 | -0.114395 | -0.222770 | -0.043240 | 0.099124 | no |
| 2026-07-23 | 29 | 0 | +0.322934 | +0.264915 | +0.438971 | 0.109414 | no |
| 2026-07-22 | 29 | 29 | -0.234811 | -0.304871 | -0.148331 | 0.082211 | no |

### Two-control endpoint

| Trading day | LOO estimates | Negative count | Median | Min | Max | Max abs change | Any sign flip? |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-07-24 | 29 | 29 | -0.110453 | -0.179697 | -0.010083 | 0.099542 | no |
| 2026-07-23 | 29 | 0 | +0.288597 | +0.254730 | +0.409964 | 0.110147 | no |
| 2026-07-22 | 29 | 29 | -0.122898 | -0.226042 | -0.033271 | 0.105204 | no |

**Result:** all three Batch-6 session signs are broad within the frozen 29-observation samples. Every ordinary leave-one-minute-out estimate stayed on the original day sign, and every controlled leave-one-minute-out estimate did the same.

This means:

- 2026-07-23 is a broad positive session, not a one-minute artifact.
- 2026-07-24 is a broad negative session, not a one-minute artifact.
- 2026-07-22 is a broad negative session, not a one-minute artifact.

## Rank-product contribution concentration

### Ordinary endpoint

| Trading day | Largest share | Top 3 | Top 5 | Largest timestamp | Largest sign |
|---|---:|---:|---:|---|---:|
| 2026-07-24 | 10.34% | 27.94% | 42.34% | 2026-07-24 13:57:00+00:00 | +1 |
| 2026-07-23 | 11.33% | 28.86% | 43.83% | 2026-07-23 13:52:00+00:00 | +1 |
| 2026-07-22 | 11.64% | 29.28% | 43.35% | 2026-07-22 13:51:00+00:00 | -1 |

### Two-control endpoint

| Trading day | Largest share | Top 3 | Top 5 | Largest timestamp | Largest sign |
|---|---:|---:|---:|---|---:|
| 2026-07-24 | 12.54% | 26.49% | 38.43% | 2026-07-24 13:39:00+00:00 | -1 |
| 2026-07-23 | 11.48% | 29.50% | 42.24% | 2026-07-23 13:46:00+00:00 | +1 |
| 2026-07-22 | 12.39% | 27.86% | 40.88% | 2026-07-22 13:59:00+00:00 | -1 |

No day is dominated by a single observation. Largest single absolute-contribution shares are roughly 9%-12% ordinary and 11%-13% controlled, while top-five shares remain roughly 38%-44%.

## Frozen adjudication

The audit answers all four pre-specified questions cleanly:

1. **2026-07-23 positive ordinary association is broad.** All 29 leave-one-minute-out ordinary estimates remain positive, ranging +0.264915 to +0.438971, with moderate contribution concentration.
2. **2026-07-24 negative ordinary association is broad.** All 29 leave-one-minute-out ordinary estimates remain negative, ranging -0.222770 to -0.043240, with moderate contribution concentration.
3. **2026-07-22 negative ordinary association is broad.** All 29 leave-one-minute-out ordinary estimates remain negative, ranging -0.304871 to -0.148331, with moderate contribution concentration.
4. The controls explain meaningful ranked hedge variation on 2026-07-24 (R² 0.329) and 2026-07-22 (R² 0.280), less on 2026-07-23 (R² 0.138), while ranked target R² remains lower on all three days. These are decomposition diagnostics only.

## Scientific interpretation

Batch 6 now supplies another clean demonstration that broad opposite-sign sessions recur under the exact same construction. The positive 2026-07-23 session is not an isolated minute artifact, just as the negative 2026-07-24 and 2026-07-22 sessions are not isolated-minute artifacts.

Together with the earlier Batch-5 audit, the cumulative post-validation evidence includes broad positive, broad negative, and near-zero/fragile sessions under the same fixed signal construction. This materially strengthens the session-heterogeneity interpretation and argues against any universal or consistently dominant directional sign rule.

The next research problem is therefore not to rescue a negative sign. It is to determine whether session state can be characterized prospectively using information available before or during the opening window, under a development/holdout discipline that prevents regime-filter overfitting.

## Limits

The official Batch-6 validation result remains unchanged. No observation is removed or relabeled. No regime classifier is created by this audit.

`hedge_delta_units` remains an inferred liquidity-provider/dealer-hedge proxy. OPRA does not identify dealer inventory or executed underlying hedge trades. Correlation, residualization, leave-one-out stability, contribution concentration, and broad session signs do not establish causality or a production trading edge.
