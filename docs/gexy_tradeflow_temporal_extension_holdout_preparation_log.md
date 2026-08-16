# GEXY temporal-extension holdout preparation log

## Purpose

This log records post-acquisition preparation of the frozen temporal-extension holdout dates without revealing or adjudicating Endpoint B. The holdout remains governed by the frozen protocol and the completed acquisition/cost plan.

Reserved dates, in frozen order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

No endpoint value is to be inspected until extraction, tradeflow feature construction, Greek-hedge construction, and frozen preparation/coverage checks are complete.

## Stage 4A — local TCBBO extraction and frozen aggressor classification

The extractor reads only the already-purchased local TCBBO DBN files. It makes no market-data requests. Trade direction is inferred only from trade price versus the pre-trade consolidated NBBO under the frozen classifier; UNKNOWN observations remain UNKNOWN and are not force-classified.

### 2026-07-21 — complete

Executed local-only command:

```powershell
uv run --with databento --with pandas python scripts/gexy_tradeflow_extract.py --date 2026-07-21 --windows 09:30-10:00 --strike-band-points 200
```

Observed extraction summary:

| Metric | Value |
|---|---:|
| Records | 125,902 |
| Unique symbols | 128 |
| Chain matches | 125,902 |
| Chain match pct | 1.000000 |
| Buy trades | 44,807 |
| Sell trades | 56,224 |
| Unknown trades | 24,871 |
| Unknown trade pct | 0.197543 |
| Contract volume | 335,831 |
| Buy contract volume | 111,200 |
| Sell contract volume | 164,417 |
| Unknown contract volume | 60,214 |
| Net signed contracts | -53,217 |
| Gross premium notional | $239,037,875 |
| Net signed premium notional | -$2,361,240 |
| Opening forward | 7481.846627 |

Local outputs:

- `data/gexy/tradeflow/gexy_spxw_2026-07-21_0930_1000_tcbbo_classified.csv`
- `data/gexy/tradeflow/gexy_spxw_2026-07-21_tcbbo_summary.csv`

Quality note: chain matching is 100%. The 19.7543% UNKNOWN-trade share is preserved by design rather than reassigned. This extraction is a preparation artifact only and does not reveal Endpoint B.

### 2026-07-20 — complete

Executed local-only command:

```powershell
uv run --with databento --with pandas python scripts/gexy_tradeflow_extract.py --date 2026-07-20 --windows 09:30-10:00 --strike-band-points 200
```

Observed extraction summary:

| Metric | Value |
|---|---:|
| Records | 142,204 |
| Unique symbols | 136 |
| Chain matches | 142,204 |
| Chain match pct | 1.000000 |
| Buy trades | 50,604 |
| Sell trades | 63,183 |
| Unknown trades | 28,417 |
| Unknown trade pct | 0.199833 |
| Contract volume | 399,199 |
| Buy contract volume | 130,198 |
| Sell contract volume | 196,557 |
| Unknown contract volume | 72,444 |
| Net signed contracts | -66,359 |
| Gross premium notional | $263,469,897 |
| Net signed premium notional | -$7,931,051 |
| Opening forward | 7501.515003 |

Local outputs:

- `data/gexy/tradeflow/gexy_spxw_2026-07-20_0930_1000_tcbbo_classified.csv`
- `data/gexy/tradeflow/gexy_spxw_2026-07-20_tcbbo_summary.csv`

Quality note: chain matching is 100%. The 19.9833% UNKNOWN-trade share is preserved by design rather than reassigned. This extraction is a preparation artifact only and does not reveal Endpoint B.

### 2026-07-17 — complete

Executed local-only command:

```powershell
uv run --with databento --with pandas python scripts/gexy_tradeflow_extract.py --date 2026-07-17 --windows 09:30-10:00 --strike-band-points 200
```

Observed extraction summary:

| Metric | Value |
|---|---:|
| Records | 150,242 |
| Unique symbols | 153 |
| Chain matches | 150,242 |
| Chain match pct | 1.000000 |
| Buy trades | 54,510 |
| Sell trades | 64,920 |
| Unknown trades | 30,812 |
| Unknown trade pct | 0.205082 |
| Contract volume | 428,852 |
| Buy contract volume | 142,369 |
| Sell contract volume | 197,381 |
| Unknown contract volume | 89,102 |
| Net signed contracts | -55,012 |
| Gross premium notional | $414,093,201 |
| Net signed premium notional | $4,541,906 |
| Opening forward | 7449.975000 |

Local outputs:

- `data/gexy/tradeflow/gexy_spxw_2026-07-17_0930_1000_tcbbo_classified.csv`
- `data/gexy/tradeflow/gexy_spxw_2026-07-17_tcbbo_summary.csv`

Quality note: chain matching is 100%. The 20.5082% UNKNOWN-trade share is preserved by design rather than reassigned. This extraction is a preparation artifact only and does not reveal Endpoint B.

### Stage 4A status — complete

All three reserved temporal-extension holdout dates have completed local TCBBO extraction and frozen aggressor classification. Each date achieved 100% chain matching. UNKNOWN observations remain unforced under the frozen classifier.

## Stage 4B — causal minute tradeflow features

The Stage 4B builder reads only local classified TCBBO CSVs and cached replay data. Flow during minute M is timestamped M+1 before the exact-timestamp replay/label join. Forward-return label columns are written to the local feature CSV as required by the frozen pipeline but are hidden from terminal output by default during holdout preparation.

### 2026-07-21 — complete

Executed local-only command:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_features.py --date 2026-07-21 --windows 09:30-10:00
```

Observed preparation summary:

| Metric | Value |
|---|---:|
| Completed flow minutes | 30 |
| Replay-matched minutes | 30 |
| Replay match pct | 100.0% |
| Frozen flow features | 19 |
| Causal alignment | minute M flow timestamped M+1 |
| Terminal forward-return labels | hidden |

Local output:

- `data/gexy/tradeflow/gexy_spxw_2026-07-21_tradeflow_minute_features.csv`

Quality note: all 30 completed opening-window flow minutes matched cached replay state exactly. The builder reported that forward-return label values were written to the local feature CSV but not displayed. No Endpoint B was inspected or adjudicated.

### 2026-07-20 — complete

Executed local-only command:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_features.py --date 2026-07-20 --windows 09:30-10:00
```

Observed preparation summary:

| Metric | Value |
|---|---:|
| Completed flow minutes | 30 |
| Replay-matched minutes | 30 |
| Replay match pct | 100.0% |
| Frozen flow features | 19 |
| Causal alignment | minute M flow timestamped M+1 |
| Terminal forward-return labels | hidden |

Local output:

- `data/gexy/tradeflow/gexy_spxw_2026-07-20_tradeflow_minute_features.csv`

Quality note: all 30 completed opening-window flow minutes matched cached replay state exactly. The builder reported that forward-return label values were written to the local feature CSV but not displayed. No Endpoint B was inspected or adjudicated.

### 2026-07-17 — complete

Executed local-only command:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_features.py --date 2026-07-17 --windows 09:30-10:00
```

Observed preparation summary:

| Metric | Value |
|---|---:|
| Completed flow minutes | 30 |
| Replay-matched minutes | 30 |
| Replay match pct | 100.0% |
| Frozen flow features | 19 |
| Causal alignment | minute M flow timestamped M+1 |
| Terminal forward-return labels | hidden |

Local output:

- `data/gexy/tradeflow/gexy_spxw_2026-07-17_tradeflow_minute_features.csv`

Quality note: all 30 completed opening-window flow minutes matched cached replay state exactly. The builder reported that forward-return label values were written to the local feature CSV but not displayed. No Endpoint B was inspected or adjudicated.

### Stage 4B status — complete

All three reserved dates have completed the frozen causal minute tradeflow feature build. Each date produced 30 completed opening-window minutes with 30/30 exact replay matches. The M to M+1 causal alignment was preserved, and forward-return label values remained hidden from terminal output during preparation.

## Stage 4C — Black76 Greek-weighted hedge proxy features and coverage

The Stage 4C builder reads only local classified TCBBO CSVs and cached replay state. It computes completed-minute Black76 delta/gamma hedge proxies using the frozen sign convention and writes forward-return labels to the local hedge-feature CSV while hiding those labels from terminal output by default.

The frozen 90% Greek-volume rule is an inclusion rule: Endpoint B uses only opening-window minutes whose `hedge_greek_solved_contract_volume_pct` is at least 0.90. A minute below the threshold is excluded; the protocol does not require every opening-window minute to meet 90%.

### 2026-07-21 — hedge build complete; coverage eligibility verified

Executed local-only hedge build:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_hedge_features.py --date 2026-07-21 --windows 09:30-10:00
```

Local output:

- `data/gexy/tradeflow/gexy_spxw_2026-07-21_tradeflow_hedge_features.csv`

Holdout-safe coverage inspection read only `flow_minute`, `timestamp`, and `hedge_greek_solved_contract_volume_pct`; no forward-return labels were read or displayed.

Observed coverage preparation summary:

| Metric | Value |
|---|---:|
| Total opening-window minutes | 30 |
| Eligible minutes at >=90% Greek-volume coverage | 29 |
| Excluded minutes below 90% | 1 |
| Median Greek-volume coverage | 99.788056% |
| Raw minimum Greek-volume coverage | 0.000000% |
| Excluded flow minute | 2026-07-21 13:30:00+00:00 |
| Excluded feature timestamp | 2026-07-21 13:31:00+00:00 |
| Excluded-minute coverage | 0.000000% |

Quality/adjudication note: the single 0%-coverage minute is not repaired, imputed, substituted, or used to alter the frozen threshold. It is excluded exactly under the pre-specified >=90% per-minute sample rule. The remaining 29 minutes are eligible for the eventual holdout endpoint calculation. No forward-return label or Endpoint B value has been inspected.

### 2026-07-20 — hedge build complete; coverage eligibility verified

Executed local-only hedge build:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_hedge_features.py --date 2026-07-20 --windows 09:30-10:00
```

Observed hedge-build summary:

| Metric | Value |
|---|---:|
| Symbol-minute Greek snapshots | 2,988 |
| Greeks solved | 2,774 / 2,988 (92.8%) |
| Median classified volume with Greeks | 99.9% |
| Raw minimum classified volume with Greeks | 0.0% |
| Completed hedge-flow minutes | 30 |
| Replay-matched availability minutes | 30 / 30 |
| Core hedge features | 15 |
| Greek-volume quality fields | 2 |
| Causal alignment | minute M quotes/flow/state timestamped M+1 |
| Terminal forward-return labels | hidden |

Local output:

- `data/gexy/tradeflow/gexy_spxw_2026-07-20_tradeflow_hedge_features.csv`

Holdout-safe eligibility inspection read only `flow_minute`, `timestamp`, and `hedge_greek_solved_contract_volume_pct`; no forward-return labels were read or displayed.

Observed coverage eligibility summary:

| Metric | Value |
|---|---:|
| Total opening-window minutes | 30 |
| Eligible minutes at >=90% Greek-volume coverage | 29 |
| Excluded minutes below 90% | 1 |
| Excluded flow minute | 2026-07-20 13:30:00+00:00 |
| Excluded feature timestamp | 2026-07-20 13:31:00+00:00 |
| Excluded-minute coverage | 0.000000% |

Quality/adjudication note: the single 0%-coverage minute is not repaired, imputed, substituted, or used to alter the frozen threshold. It is excluded exactly under the pre-specified >=90% per-minute sample rule. The remaining 29 minutes are eligible for the eventual holdout endpoint calculation. No forward-return label or Endpoint B value has been inspected.

### Remaining Stage 4C work

- 2026-07-17: Black76 hedge build and holdout-safe coverage verification pending.

## Next frozen preparation steps

1. complete Stage 4C Black76 hedge build and coverage eligibility check for 2026-07-17;
2. verify the dedicated holdout validator applies the frozen 09:30-10:00, >=90%-coverage, 15-minute Endpoint-B sample exactly;
3. only after all preparation safeguards pass, reveal all three untouched Endpoint-B values together in one dedicated invocation.

## Scientific guardrails

- OPRA does not identify observed customer/dealer inventory or ground-truth trade aggressor.
- Databento vendor-side fields are not treated as ground-truth aggressor direction.
- Dealer/LP hedge quantities are proxies, not observed hedge executions.
- No sign convention is changed after inspecting results.
- No causal or trading-edge claim is made from correlation alone.
