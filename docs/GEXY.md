# GEXY v1

GEXY is the SPX options hedge-pressure research engine in EFI-AI. It combines the live SPX/SPXW option surface with GEX/GAX-style structural features, records forecasts, resolves them against later SPX reference observations, and exposes the results in a local operator UI.

## Safety posture

GEXY v1 is research/paper-only. It does not place trades or enable automatic execution. Model confidence is a model score, not a guaranteed probability of success. Fine horizons remain shadow-only unless conservative evidence gates qualify them for manual review.

## Start the operator screen

From PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\gexy_launch.ps1
```

The launcher starts the local FastAPI service and opens:

```text
http://127.0.0.1:8765/
```

The UI reads the real GEXY prediction journals. Production horizons are 5, 15, 30 and 60 minutes. The shadow research grid is adjustable from 1 through 60 minutes in one-minute increments.

The main chart reconstructs sampled candles from GEXY's SPX reference observations and overlays the selected forecast. These are not exchange-native OHLC candles. The optional prediction panel separately plots the history of expected SPX moves for the selected horizon.

## Stop the operator screen

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\gexy_stop.ps1
```

## Run the final readiness check

```powershell
python scripts\gexy_finish_check.py --strict-data
```

A ready result confirms the operator API/UI, launcher, backtest command, production horizon set, 1-60 minute shadow grid and the presence of both production and shadow journal data.

## Run a frozen-journal backtest

All shadow horizons:

```powershell
python scripts\gexy_backtest_report.py --source shadow
```

A specific fine horizon:

```powershell
python scripts\gexy_backtest_report.py --source shadow --horizon 5
```

Production journal:

```powershell
python scripts\gexy_backtest_report.py --source production
```

The report scores predictions that were already written before their realized outcomes. It reports directional accuracy, resolution coverage, MAE, RMSE, bias, confidence/calibration gap, a naive constant-direction baseline and lift versus that baseline, plus chronological 60/20/20 diagnostic splits.

## Live collection

The Windows Scheduled Task `GEXY Session Collector` is the live data collector. It is scheduled on weekdays before the regular SPX session and writes:

- `data/gexy/live_predictions.jsonl` — production-horizon predictions
- `data/gexy/shadow_predictions.jsonl` — fine 1-60 minute research predictions
- `data/gexy/gax_shadow.jsonl` — GAX shadow research journal
- `data/gexy/logs/` — session logs

The collector resolves due predictions before writing the next observation and uses the Alpaca calendar guard for holidays and early closes.

## Qualification

Fine horizons are not promoted because of a single good session. The qualification layer requires multi-session evidence, a high Wilson lower bound, sufficient resolved observations and coverage, positive lift over a naive baseline, and cross-session lift stability. Automatic promotion remains disabled; passing horizons are eligible only for manual review.

## Current limitation

GEXY can be operationally complete while the forecasting model is still empirically unqualified. A working UI or completed backtest is not evidence of a high success rate. Model changes should be judged by out-of-sample and cross-session evidence rather than by one-session headline accuracy.
