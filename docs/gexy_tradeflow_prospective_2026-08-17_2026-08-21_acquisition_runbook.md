# GEXY prospective 2026-08-17 through 2026-08-21 acquisition runbook

## Purpose

Freeze the acquisition/preparation sequence for the prospective five-session block before any prospective Endpoint-B result is available.

Prospective dates remain fixed:

1. 2026-08-17
2. 2026-08-18
3. 2026-08-19
4. 2026-08-20
5. 2026-08-21

This runbook does not authorize any paid market-data request. Every paid step requires a fresh metadata price and a separately reviewed explicit cap before execution.

## Per-date acquisition sequence

For each fixed date, use the same proven pipeline and frozen research construction used for the prior temporal-extension holdout.

### Stage 1 — metadata-only price plan first

Run the default cost planner for the date, with no paid-build flag:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates YYYY-MM-DD
```

The script's default mode makes metadata cost-estimate calls only and downloads no market data. Record the exact definition cost, statistics cost, metadata total, local chain status, and any exact-symbol CBBO estimate available from an already-cached chain.

Do not add `--build-missing-chains` until the reported definition+OI estimate has been reviewed and an explicit cap has been frozen.

### Stage 2 — chain definition/OI acquisition only after reviewed cap

If the chain is missing, rerun only after separately reviewing the fresh metadata estimate:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates YYYY-MM-DD --build-missing-chains --max-metadata-download-cost REVIEWED_CAP
```

The planner must re-price immediately before the download and fail closed if the re-priced total exceeds the explicit cap.

After chain creation, record the exact SPXW 0DTE contract count and exact-symbol full-day CBBO estimate.

### Stage 3 — exact-symbol full-day CBBO

Use the existing `gexy_multiday_replay.py` workflow only after reviewing a fresh exact-symbol CBBO estimate and freezing a separate explicit cap. No paid replay command is authorized by this document alone.

### Stage 4 — opening TCBBO

Use the frozen opening scope only:

- OPRA TCBBO;
- 09:30-10:00 America/New_York;
- SPXW 0DTE exact symbols;
- opening fitted forward +/-200 SPX points;
- same chain/exact-symbol logic.

Use `gexy_tradeflow_plan.py` / `gexy_tradeflow_download.py` under the existing fail-closed pricing/download discipline. Review a fresh per-date TCBBO estimate and freeze an explicit cap before any paid `--execute` invocation.

### Stage 5 — local-only preparation

After required data are local, run the same frozen local pipeline:

1. TCBBO extraction / frozen aggressor classification;
2. causal minute tradeflow features, M to M+1;
3. Black76 Greek-weighted hedge features;
4. holdout-safe Greek-volume coverage inspection.

Forward-return label values must remain hidden during preparation. UNKNOWN trade directions remain UNKNOWN. No repair, imputation, alternate window, alternate horizon, alternate coverage threshold, sign flip, or date substitution is permitted.

## Reveal discipline

- Do not compute or inspect any prospective Endpoint-B value after an individual date is prepared.
- All five dates must be fully prepared first.
- Run the dedicated prospective validator in default safe-preflight mode only after all five dates are complete.
- Only after safe preflight passes may the dedicated `--reveal` mode be invoked.
- The validator must reveal all five prospective Endpoint-B values together.
- Record the official five-date adjudication before any post-hoc analysis.

## First fixed action for 2026-08-17

After the 2026-08-17 session data are available for historical planning, the first command is exactly:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-08-17
```

This first action is metadata pricing only. It is not a paid data download and it does not evaluate Endpoint B.
