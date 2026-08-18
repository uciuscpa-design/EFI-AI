# GEXY cumulative opening heterogeneity characterization result

## Status

This document records the completed frozen cumulative characterization across the same 17 already-seen opening sessions. The characterization was local-only, used the unchanged opening 15-minute construction and 90% classified-volume Greek coverage floor, and did not inspect or acquire the reserved holdout dates 2026-07-21, 2026-07-20, or 2026-07-17.

The safeguard suite passed 3/3 immediately before execution after a CLI help-format repair only. That repair changed no dates, endpoint mathematics, leave-one-minute-out calculations, stability categories, or data access.

## Frozen aggregate result

Across 17 already-seen sessions:

- ordinary Endpoint-B negative days: **13 / 17**
- ordinary Endpoint-B positive days: **4 / 17**
- exact-zero days: **0 / 17**
- strict sign-stable negative days: **12 / 17**
- strict sign-stable positive days: **3 / 17**
- sign-fragile days: **2 / 17**
- days with at least 80% same-sign ordinary leave-one-minute-out estimates: **16 / 17**

Ordinary Endpoint-B distribution:

- median: **-0.144335**
- minimum: **-0.486700**
- maximum: **+0.329557**
- sample standard deviation: **0.226574**
- Q1: **-0.230542**
- Q3: **-0.063547**
- IQR: **0.166995**

Median ordinary rank-product contribution concentration across the 17 days:

- largest single absolute-contribution share: **0.107438**
- top-three absolute-contribution share: **0.283553**
- top-five absolute-contribution share: **0.425583**

## Day-level stability pattern

Strict sign-stable negative sessions:

- 2026-08-13: -0.144335
- 2026-08-12: -0.401970
- 2026-08-10: -0.090640
- 2026-08-07: -0.356650
- 2026-08-06: -0.209360
- 2026-08-05: -0.486700
- 2026-08-04: -0.418719
- 2026-08-03: -0.136453
- 2026-07-30: -0.145813
- 2026-07-27: -0.194581
- 2026-07-24: -0.123645
- 2026-07-22: -0.230542

Strict sign-stable positive sessions:

- 2026-07-31: +0.272906
- 2026-07-28: +0.130542
- 2026-07-23: +0.329557

Sign-fragile sessions:

- 2026-08-11: full-sample -0.063547; 27/29 ordinary LOO estimates retained the negative sign, with range -0.142310 to +0.007115
- 2026-07-29: full-sample +0.000985; only 13/29 ordinary LOO estimates retained the positive sign, with range -0.062397 to +0.073892

The near-zero 2026-07-29 session is the clearest genuinely fragile case. 2026-08-11 is weakly negative and only narrowly fails the strict category.

## Interpretation

The cumulative seen sample contains recurrent broad opposite-sign sessions under the same frozen construction. This is no longer well described as isolated minute-level outlier behavior:

- **12** sessions are strictly stable negative under every one-minute deletion;
- **3** sessions are strictly stable positive under every one-minute deletion;
- only **2** sessions are sign-fragile.

Therefore the most defensible descriptive statement is:

> Broad negative opening hedge/return associations are more frequent in this 17-day seen sample, but broad positive opening associations also recur under the unchanged construction.

The negative state has a strong observed base-rate asymmetry (13/17 full-sample negative; 12/17 strict-stable negative), but this does not justify a universal negative trading rule because three materially positive sessions are also strict sign-stable and a fourth positive day is near zero/sign-fragile.

The contribution concentration summary is not extreme: the median largest single absolute contribution is about 10.7%, while the median top five account for about 42.6%. Combined with the leave-one-minute-out results, there is no general evidence that the recurring strict positive/negative session signs are artifacts of one exceptional minute.

## Relationship to failed 09:40 state screen

The separately frozen 09:40 six-descriptor development screen selected **no candidate**. That result remains unchanged. The present characterization strengthens the evidence that the session-level heterogeneity itself is real within the already-seen sample, while the tested simple early-opening summaries were insufficient to anticipate it prospectively.

Do not respond by lowering the prior development threshold, changing the 09:40 cutoff, combining the rejected descriptors, or using the reserved holdout block to tune a replacement rule.

## Reserved holdout

The reserved dates remain untouched:

- 2026-07-21
- 2026-07-20
- 2026-07-17

No purchase or inspection is authorized by this result.

## Scientific limits

All 17 dates are already-seen development data. The stability categories are descriptive influence diagnostics, not independent statistical tests, because the minute-level 15-minute forward-return labels overlap.

`hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy derived from OPRA trade price versus pre-trade NBBO and Black-76 Greeks. The result does not establish observed dealer inventory, executed hedge flow, causality, or a production trading edge.
