# GEXY temporal-extension holdout preflight record

## Status

Frozen holdout-safe preflight completed successfully before Endpoint-B reveal.

Reserved dates, in frozen reveal order:

1. 2026-07-21
2. 2026-07-20
3. 2026-07-17

The preflight used `scripts/gexy_tradeflow_temporal_extension_holdout_validator.py` in its default mode, without `--reveal`.

## Frozen rules verified

- opening window: 09:30-10:00 America/New_York only;
- horizon: 15 minutes only;
- minimum classified-volume Greek coverage: 90%;
- target locked: `forward_return_15m_bps`;
- signal locked: `hedge_delta_units`;
- August reference median locked: -0.209360;
- 17-session seen chronology artifact present and matching the frozen sequence.

## Holdout-safe preparation check

| Trading day | Opening rows | Replay matches | Eligible >=90% | Excluded <90% | Excluded flow minute | Excluded coverage |
|---|---:|---:|---:|---:|---|---:|
| 2026-07-21 | 30 | 30 | 29 | 1 | 2026-07-21 13:30:00+00:00 | 0.0 |
| 2026-07-20 | 30 | 30 | 29 | 1 | 2026-07-20 13:30:00+00:00 | 0.0 |
| 2026-07-17 | 30 | 30 | 29 | 1 | 2026-07-17 13:30:00+00:00 | 0.0 |

Each sole excluded row remains excluded exactly under the frozen >=90% per-minute inclusion rule. No repair, imputation, substitution, alternate coverage floor, alternate horizon, or alternate window was introduced.

## Holdout boundary

The preflight explicitly reported that no forward-return label values or Endpoint-B values were read or displayed. Therefore the frozen safeguard stage is complete and the protocol-authorized next action is one dedicated `--reveal` invocation that computes all three untouched Endpoint-B values before printing any of them.

The official holdout result must be recorded before any influence or post-hoc diagnostic.

## Scientific limits

This remains a three-session descriptive temporal-extension check. `hedge_delta_units` is an inferred liquidity-provider/dealer-hedge proxy, not observed dealer inventory or executed hedge trades. Correlation does not establish causality, stationarity, or production trading edge.
