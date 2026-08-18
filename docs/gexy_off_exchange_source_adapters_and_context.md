# GEXY Off-Exchange/TRF Source Adapters and Slow Context

## Status

Implemented as an **isolated software foundation** on the GEXY branch. Nothing in this document or the accompanying modules is connected to the frozen 2026-08-17 through 2026-08-21 prospective SPXW replication. These inputs may not alter that protocol, its acquisition construction, its features, its labels, or its adjudication.

Live activation, threshold freezing, walk-forward evaluation, ensemble weighting, and forecasting use remain post-prospective work.

## Implemented modules

### `packages/gexy/off_exchange_sources.py`

Provider-specific normalizers for real-time/off-exchange equity trade data:

- **Massive stock trades**
  - vendor-specific off-exchange rule: exchange ID `4` **and** a TRF identifier is present;
  - causal availability uses the SIP timestamp;
  - participant and TRF timestamps are preserved separately when present;
  - the adapter does not infer buyer/seller direction.
- **Alpaca SIP stock trades**
  - no hard-coded default off-exchange exchange code;
  - caller must supply an explicit, verified Alpaca exchange-code allow-list;
  - causal availability uses the SIP trade timestamp;
  - IEX-only data is not accepted as a substitute for full SIP/TRF coverage.
- **Databento equity trades**
  - TRF identification is by dataset-scoped `publisher_id`;
  - current default publisher maps are isolated by dataset and can be overridden from provider metadata;
  - causal availability uses `ts_recv`, not the earlier source-event timestamp;
  - no aggressor-side inference is made from Nasdaq Basic/TRF trade records.

Current dataset-scoped Databento defaults implemented from provider metadata:

- `XNAS.BASIC`: `82 -> FINN`, `83 -> FINC`;
- `EQUS.PLUS`: `54 -> FINN`, `55 -> FINY`, `56 -> FINC`;
- `EQUS.ALL`: `68 -> FINN`, `69 -> FINY`, `70 -> FINC`.

These are provider identifiers, not universal market-center codes. Provider metadata must be re-verified before production activation.

### `scripts/gexy_off_exchange_source_capture.py`

Local capture normalizer for:

- Massive JSON/JSONL trade captures;
- Alpaca SIP JSON/JSONL trade captures;
- Databento CSV captures.

The script makes **no market-data requests**. It converts already-captured source records into the GEXY off-exchange contract and preserves the causal `available_at` timestamp basis.

## FINRA daily short-sale volume context

### `packages/gexy/finra_short_volume.py`

Implements:

- local parsing of FINRA pipe-delimited Daily Short Sale Volume files;
- explicit `available_at` supplied by the acquisition process;
- per-symbol short volume, short-exempt volume, total volume, and ratios;
- optional combination of mutually exclusive facility-level files using the latest component availability time.

Scientific interpretation is frozen in the software contract:

- short-sale volume is **not** short interest;
- short-sale volume is **not** a net short position;
- the files may omit offsetting activity that is not publicly disseminated;
- a consolidated FINRA file must not be added to its own component files, which would double-count activity.

### `scripts/gexy_finra_short_volume_context.py`

Local-only normalization CLI. The exact timezone-aware time when the file became observable to GEXY is required explicitly. No network request is made.

## SEC Form 13F slow institutional context

### `packages/gexy/institutional_13f.py`

Parses an already-downloaded SEC Form 13F INFORMATION TABLE XML document and preserves:

- issuer;
- class;
- CUSIP;
- FIGI when present;
- reported value and explicit value scale;
- shares/principal amount;
- put/call field when present;
- investment discretion;
- other-manager field;
- voting authority.

Causal availability is the **filing acceptance timestamp**, never the quarter-end report period.

13F data is classified as slow context only. It does not identify when during the quarter a position was established, whether it remained after quarter-end, or the manager's intraday trading intent.

### `scripts/gexy_13f_context.py`

Local-only SEC XML normalization CLI. No EDGAR network request is made by the script.

## Streaming architecture rule

GEXY should prefer push-based streaming over aggressive REST polling for real-time TRF intelligence.

The source adapter contract is:

`vendor stream -> raw immutable capture -> provider-specific normalization -> explicit off-exchange/TRF identification -> available_at causality -> causal large-print/off-exchange feature engine -> later walk-forward evaluation`

This deliberately separates transport from research logic. Vendor connection/authentication code may change without changing the meaning of GEXY's normalized research fields.

## Coverage and identity safeguards

- A vendor-specific exchange ID or publisher ID is never treated as a universal market identifier.
- TRF/off-exchange does not mean a specific dark pool unless the source explicitly identifies it.
- Large off-exchange prints are not automatically institutional, informed, bullish, or bearish.
- The public tape does not generally reveal the beneficial buyer/seller.
- Provider coverage must be measured. A feed containing major TRFs is not automatically assumed to represent 100% of all U.S. off-exchange activity.
- Trade corrections/cancels must eventually be incorporated into production stream state before official forecasting activation.

## Post-prospective activation sequence

1. Complete and formally record the frozen 2026-08-17 through 2026-08-21 SPXW prospective block.
2. Re-verify current provider venue/publisher metadata and entitlements.
3. Choose the first live source based on coverage, licensing, latency, and cost.
4. Capture raw data before feature transformation so the stream is auditable/replayable.
5. Validate provider adapter parity against local fixtures and real captures.
6. Add correction/cancel handling for the selected source.
7. Establish symbol universe: SPY first, then selected high-weight S&P 500 constituents/ETFs.
8. Freeze off-exchange anomaly thresholds and causal feature definitions.
9. Test the off-exchange expert alone using walk-forward data.
10. Test incremental value versus SPX/SPXW option-flow and ES MBO experts.
11. Only after untouched-forward validation may the off-exchange expert influence GEXY conviction or forecasts.

## Intended cross-market research chain

A principal post-prospective hypothesis is:

`SPX/SPXW option-flow pressure -> SPY/constituent TRF activity -> ES MBO liquidity response -> breadth/volatility confirmation -> later SPX response`

This is a hypothesis to test, not a trading rule or causal claim.
