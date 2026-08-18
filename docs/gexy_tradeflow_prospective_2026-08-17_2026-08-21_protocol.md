# GEXY prospective 2026-08-17 through 2026-08-21 replication protocol

## Status and purpose

This protocol is frozen on 2026-08-16, before the 2026-08-17 market session and before any Endpoint-B value from the five sessions below is available to this research process.

Prospective sessions, in fixed chronological order:

1. 2026-08-17
2. 2026-08-18
3. 2026-08-19
4. 2026-08-20
5. 2026-08-21

The purpose is to test whether the negative opening-window Endpoint-B clustering observed in the already-seen August sessions persists in a genuinely forward five-session block.

This is a prospective descriptive replication. It is not a fitted trading rule, a causal test, or a license to alter the previously frozen temporal-extension holdout result.

## Prior evidence that motivates the prospective question

The official temporal-extension holdout was revealed and recorded before this protocol was created.

Already-seen facts include:

- August seen-data median Endpoint B: -0.209360;
- all 9 previously available August seen sessions were negative;
- the 2026-07-17 / 2026-07-20 / 2026-07-21 untouched temporal-extension block had a 3-day median Endpoint B of +0.096059;
- after appending that block, the 20-session ordinal-time Spearman was -0.393985;
- 20/20 leave-one-day-out trend estimates retained the negative sign;
- the terminal negative run through 2026-08-13 was 9 sessions.

Because those facts are already seen, they may motivate this prospective protocol but may not be counted as prospective evidence.

## Frozen construction

For each prospective session use the same opening Endpoint-B construction used in the temporal-extension holdout:

- SPXW 0DTE only;
- OPRA TCBBO trade and pre-trade consolidated BBO construction;
- opening window 09:30-10:00 America/New_York only;
- opening fitted forward +/-200 SPX points exact-symbol strike scope;
- same cached-chain / exact-symbol logic;
- same frozen pre-trade NBBO aggressor classifier;
- UNKNOWN observations remain UNKNOWN;
- same M+1 causal feature availability;
- same Black-76 IV / Greek calculations;
- same hedge sign convention;
- minimum classified-volume Greek coverage: 90% per minute;
- minutes below 90% are excluded without repair, imputation, or substitution;
- horizon: 15 minutes only;
- signal: `hedge_delta_units`;
- target: `forward_return_15m_bps`.

No alternate window, horizon, strike band, coverage floor, aggressor rule, Greek model, sign convention, date substitution, or call/put split may be introduced after any prospective Endpoint-B value is visible.

## Frozen primary endpoint

For each session compute exactly:

**Endpoint B:** ordinary Spearman correlation between `hedge_delta_units` and `forward_return_15m_bps` on the frozen opening / >=90%-coverage sample.

Endpoint A, the historical two-control partial Spearman using `backward_return_1m_bps` and `flow_net_signed_contracts`, may be reported for continuity only and is not the prospective primary endpoint.

## Frozen prospective adjudication

### Primary persistence condition

Compute the median Endpoint-B value across the five prospective sessions.

Primary persistence support:

- prospective 5-day median Endpoint B < 0.

Primary persistence failure / weakening:

- prospective 5-day median Endpoint B >= 0.

This zero threshold is a directional descriptive threshold fixed before the five sessions are observed. It is not a trading threshold.

### Pre-declared magnitude comparison

Compare the prospective five-day median with the already-fixed August seen-data median of -0.209360.

Classify the prospective block descriptively as:

- `more_negative_than_prior_august` if median < -0.209360;
- `similar_or_weaker_negative` if -0.209360 <= median < 0;
- `nonnegative_block` if median >= 0.

This magnitude comparison is secondary. It does not replace the primary zero-sign persistence condition.

### Secondary sign composition

Report:

- negative / positive / exact-zero day counts;
- strict sign-stable negative / strict sign-stable positive / sign-fragile counts using the already-frozen leave-one-minute-out category rule;
- each day's leave-one-minute-out same-sign percentage and range.

No alternate minimum negative-day count may be introduced after results are visible.

### Secondary combined chronology

After all five prospective endpoints are revealed together, append them after 2026-08-13 to form a 25-session chronology from 2026-07-17 through 2026-08-21.

Report descriptively:

- combined 25-session ordinal-time Spearman;
- leave-one-day-out trend sign stability;
- fixed 5-session rolling medians using the already-frozen rolling-window length;
- sign runs.

These chronology diagnostics are secondary and may not override the primary prospective five-day median condition.

No p-value or independence claim is authorized.

## Acquisition and reveal discipline

1. Keep all five dates fixed; no result-driven date substitution is permitted.
2. Capture or acquire required chain, CBBO, and opening TCBBO inputs under separately reviewed cost controls.
3. No market-data purchase is authorized by this protocol alone.
4. Any paid acquisition requires fresh metadata pricing and an explicit reviewed cap before execution.
5. Acquire / capture and prepare all five sessions before revealing any prospective Endpoint-B value.
6. During preparation, terminal previews must keep forward-return label values hidden.
7. Run a dedicated holdout-safe preflight that does not read forward-return label values.
8. Reveal all five prospective Endpoint-B values together in one dedicated invocation.
9. Record the official prospective result before any post-hoc influence, feature, regime, threshold, or alternative-specification analysis.
10. If a fixed date has missing or unusable data, do not substitute another session. Record the block as incomplete until that exact date can be recovered under the frozen construction.

## Relationship to the completed temporal-extension holdout

The completed three-date temporal-extension holdout is now seen data and remains permanently governed by its own frozen protocol and official result.

Nothing in this prospective test may retroactively change that adjudication.

The new five-session block is a separate forward replication intended to reduce the risk of repeated retrospective slicing.

## Scientific limits

This five-session block remains small and descriptive. Even a successful prospective replication cannot establish statistical independence, stationarity, causality, observed dealer inventory, executed dealer hedge trades, or a production trading edge.

`hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy.

A successful block would justify further forward replication and engineering validation; it would not by itself justify live capital deployment.
