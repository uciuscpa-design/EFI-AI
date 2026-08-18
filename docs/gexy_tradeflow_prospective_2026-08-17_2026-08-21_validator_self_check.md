# GEXY prospective 2026-08-17 through 2026-08-21 validator self-check

## Status

Pre-market validator self-check completed successfully on 2026-08-16 before the 2026-08-17 market session.

The check used:

```powershell
uv run --with pandas python scripts/gexy_tradeflow_prospective_week_validator.py --self-check
```

## Frozen prospective dates

1. 2026-08-17
2. 2026-08-18
3. 2026-08-19
4. 2026-08-20
5. 2026-08-21

## Frozen rules confirmed

- opening window: 09:30-10:00 America/New_York only;
- horizon: 15 minutes only;
- minimum classified-volume Greek coverage: 90%;
- primary condition: five-day median Endpoint B < 0;
- secondary August reference median: -0.209360;
- target: `forward_return_15m_bps`;
- signal: `hedge_delta_units`.

## Future-file presence at self-check

| Trading day | Raw feature file present | Hedge feature file present |
|---|---|---|
| 2026-08-17 | False | False |
| 2026-08-18 | False | False |
| 2026-08-19 | False | False |
| 2026-08-20 | False | False |
| 2026-08-21 | False | False |

This absence is expected before the prospective sessions are captured/prepared and confirms that the validator was checked before future feature artifacts existed locally.

## Self-check result

The validator reported:

- `SELF-CHECK PASS: official 20-session base chronology matches the frozen sequence.`
- `PROSPECTIVE SAFETY: no future feature contents, forward-return label values, or future Endpoint-B values were read.`
- `NO PAID DATA REQUESTS: local file-presence/base-date checks only.`

## Scientific boundary

The validator and prospective protocol are now frozen before the first prospective session. Future preparation may create the required raw and hedge feature artifacts, but the window, horizon, coverage rule, primary condition, signal, target, date block, and reveal discipline must not be altered after prospective outcomes become available.

All five dates must be fully prepared before any prospective Endpoint-B value is revealed. The eventual reveal must compute and display all five dates together and the official prospective result must be recorded before any post-hoc diagnostics.
