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

### Remaining Stage 4A work

- 2026-07-20: extraction pending.
- 2026-07-17: extraction pending.

## Next frozen preparation steps

1. complete local TCBBO extraction for 2026-07-20 and 2026-07-17;
2. build the frozen tradeflow feature layer from the classified files;
3. build Black76 Greek-weighted hedge proxy features using the frozen hedge sign convention;
4. verify the frozen Greek-volume coverage requirement, including the 90% coverage floor;
5. only after all preparation checks pass, run the dedicated holdout reveal.

## Scientific guardrails

- OPRA does not identify observed customer/dealer inventory or ground-truth trade aggressor.
- Databento vendor-side fields are not treated as ground-truth aggressor direction.
- Dealer/LP hedge quantities are proxies, not observed hedge executions.
- No sign convention is changed after inspecting results.
- No causal or trading-edge claim is made from correlation alone.
