# GEXY prospective 2026-08-17 historical-availability attempt

## Status

A metadata-only pricing attempt for 2026-08-17 was made early, on 2026-08-16, before Databento had released that OPRA historical date.

Command:

```powershell
uv run --with databento --with pandas python scripts/gexy_multiday_plan.py --dates 2026-08-17
```

Observed Databento response:

- error type: `422 data_start_after_available_end`;
- requested start: `2026-08-17 00:00:00+00:00`;
- OPRA.PILLAR available end reported by Databento: `2026-08-15 00:00:00+00:00`.

## Interpretation

This is a historical-data availability rejection, not a GEXY pipeline failure and not a paid download failure. The planner was still in its default metadata-pricing mode and no `--build-missing-chains` or other paid-download flag was supplied.

No prospective feature file, forward-return label value, or Endpoint-B value was created or inspected by this attempt.

The fixed next action remains the same metadata-only planner command, but only after Databento's OPRA.PILLAR available range includes 2026-08-17.

No paid acquisition is authorized until that metadata-only plan succeeds and a fresh cost is separately reviewed and capped.
