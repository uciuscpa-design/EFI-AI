# GEXY Off-Exchange Live Streaming Capture

## Status

Implemented in isolation. **Not activated as a forecasting input and not connected to the frozen 2026-08-17 through 2026-08-21 prospective SPXW protocol.**

## Push-first transport

GEXY now has a push-stream capture foundation for U.S. equity trade data rather than a high-frequency REST polling loop.

Implemented:

- `packages/gexy/off_exchange_streaming.py`
  - Massive and Alpaca authentication/subscription message builders;
  - WebSocket payload decoding;
  - immutable raw-record receive stamping;
  - `gexy_received_at` causal clock;
  - enforcement that live `available_at` can never precede GEXY client receipt.
- `packages/gexy/off_exchange_live_normalization.py`
  - Massive live-capture normalization;
  - Alpaca SIP live-capture normalization;
  - trade-ID matching from raw capture to normalized record;
  - `available_at=max(provider-derived time, gexy_received_at)`.
- `scripts/gexy_off_exchange_live_capture.py`
  - raw JSONL WebSocket capture for Massive or Alpaca SIP;
  - defaults to dry-run/fail-closed;
  - `--connect` is required before any network connection opens;
  - writes raw source messages before feature transformation;
  - never prints API secrets.
- `scripts/gexy_off_exchange_live_normalize.py`
  - local normalization of the raw live capture;
  - no network requests;
  - preserves provider timestamps and true GEXY receive causality.

## Provider activation gates

### Massive

The capture CLI supports the provider's stock WebSocket endpoints. Real-time versus delayed access depends on the selected account plan. GEXY does not attempt to bypass access controls or rate limits.

Off-exchange identification remains provider-specific: exchange ID `4` plus a TRF identifier.

### Alpaca SIP

The capture CLI uses the Alpaca SIP stock WebSocket endpoint. SIP entitlement must exist on the account. An IEX-only feed is not treated as equivalent to SIP/TRF coverage.

The off-exchange exchange-code allow-list remains explicit and must be verified from Alpaca exchange metadata before activation. No universal `D` rule is embedded in the core analytics.

### Databento

The provider adapter supports Databento TRF publisher IDs for normalized captures, but the new generic WebSocket capture CLI intentionally does **not** open a Databento live stream.

Databento live activation remains a separate reviewed step because entitlements and cost can differ by dataset/service. Any paid or metered Databento step still requires a fresh cost/access review and explicit user authorization under the existing GEXY acquisition safeguards.

## Causal timestamp hierarchy

For historical/local captures without a GEXY client receive time, the provider adapter uses the best available dissemination/capture timestamp:

- Massive: SIP timestamp;
- Alpaca SIP: SIP trade timestamp;
- Databento: `ts_recv`.

For actual live GEXY captures, the raw stream is additionally stamped with `gexy_received_at` and normalized live availability becomes:

`available_at = max(provider-derived availability, gexy_received_at)`

This prevents network/provider latency from being accidentally converted into look-ahead information.

## Raw-first audit rule

Production research should preserve the immutable raw stream before feature creation:

`WebSocket/native stream -> raw timestamped capture -> provider adapter -> TRF/off-exchange normalization -> causal features`

The raw record is the audit source for later replay, correction handling, latency measurement, and provider-parity checks.

## Required work before forecast activation

The live foundation is implemented, but official forecasting activation still requires:

1. complete the frozen Aug. 17-21 prospective replication first;
2. verify provider entitlements and current exchange/publisher metadata;
3. choose a controlled symbol universe, beginning with SPY;
4. capture representative live data without feeding it into the frozen experiment;
5. validate raw-to-normalized parity;
6. implement and test trade correction/cancel state handling for the selected feed;
7. measure end-to-end latency and missing-message behavior;
8. freeze anomaly thresholds/features;
9. walk-forward test the off-exchange expert independently;
10. prospectively test incremental value before ensemble/conviction use.

Passing software tests will verify implementation contracts only. It will not establish predictive value.
