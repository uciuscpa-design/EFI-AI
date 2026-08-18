# GEXY prospective 2026-08-17 historical-availability attempt

## Status

This record preserves the availability and licensing gates encountered while preparing the fixed 2026-08-17 session for the frozen GEXY prospective block.

No prospective feature file, forward-return label value, or Endpoint-B value was created or inspected during any attempt recorded here.

## Early metadata-only availability attempt

A metadata-only pricing attempt for 2026-08-17 was made early, on 2026-08-16, before Databento had released that OPRA historical date.

Command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-08-17
```

Observed Databento response:

- error type: `422 data_start_after_available_end`;
- requested start: `2026-08-17 00:00:00+00:00`;
- OPRA.PILLAR available end reported by Databento: `2026-08-15 00:00:00+00:00`.

Interpretation: historical-data availability rejection only. The planner was in default metadata-pricing mode and no paid-download flag was supplied.

## 2026-08-17 later availability progression

A later metadata-only attempt reached Databento after the dataset had advanced into the 2026-08-17 session but before the planner's frozen full-day definition endpoint was available.

Observed response:

- error type: `422 data_end_after_available_end`;
- OPRA.PILLAR available end reported: `2026-08-17 22:30:00+00:00`;
- planner definition-request end: `2026-08-18 00:00:00+00:00`.

No paid download was requested by that attempt.

A subsequent metadata-only rerun succeeded and produced this fresh cost plan:

- definition cost estimate: `$0.034114`;
- statistics/OI cost estimate: `$0.012558`;
- total definition+OI estimate: `$0.046673`;
- chain status: `missing`;
- exact-symbol CBBO cost: not yet available because the chain had not been built.

The default planner mode made metadata cost-estimate calls only and downloaded no market data.

## Explicitly capped chain-build attempt

After separately reviewing the fresh `$0.046673` estimate, the user explicitly approved a hard maximum of `$0.05` for the 2026-08-17 definition+OI chain build only.

Command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-08-17 --build-missing-chains --max-metadata-download-cost 0.05
```

The planner immediately re-priced the missing-chain metadata before download:

- definition: `$0.034114`;
- statistics: `$0.012558`;
- total: `$0.046673`;
- hard guard: `$0.050000`.

The preflight passed because the refreshed estimate remained below the approved cap.

The first time-series definition request then failed with:

- HTTP status: `403`;
- Databento error: `license_not_found_unauthorized`;
- message: a live-data license is required to access OPRA.PILLAR data after `2026-08-17T13:30:00.000000000Z`.

The exception occurred inside `_build_chain` during the definition `timeseries.get_range` call, before the chain-save step. Therefore no new 2026-08-17 chain CSV was produced by this attempt.

Billing status for the failed time-series request is intentionally not inferred from the exception alone. No successful data payload was observed in the terminal output. Exact account usage, if needed, should be verified against Databento's Data Usage/Billing portal rather than assumed.

## Scientific interpretation and next action

This is a licensing-age gate, not evidence of a GEXY model or pipeline failure. The prospective construction remains frozen and unchanged.

Do not shorten the full-day definition interval, substitute another acquisition window, change the date, or enable a different live-data path merely to bypass this gate. The next attempt should preserve the same planner and same 2026-08-17 construction after the requested range has aged sufficiently into Databento historical access.

No CBBO or TCBBO purchase is authorized by this record. Any later paid step still requires a new fresh estimate, separate review, and explicit hard cap.
