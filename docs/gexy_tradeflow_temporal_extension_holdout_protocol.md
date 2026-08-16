# GEXY temporal-extension holdout protocol

## Status and purpose

This protocol is frozen after the 17-seen-session chronological-drift characterization was completed and permanently recorded, and before any pricing, acquisition, preparation, or endpoint inspection for the reserved dates below.

The three dates were reserved before the failed 09:40 session-state development screen and have remained unread/unpurchased throughout the cumulative heterogeneity and chronological-drift work:

1. **2026-07-21**
2. **2026-07-20**
3. **2026-07-17**

They are now reassigned, before inspection, to a different untouched question:

> Does the temporal clustering / negative chronological tendency observed from 2026-07-22 through 2026-08-13 extend backward into the immediately preceding untouched three-session block?

This is an out-of-sample temporal-extension check for the descriptive drift finding. It is not a validation of the failed 09:40 descriptor screen and not a new predictor search.

## Provenance of the hypothesis

The seen-data chronology showed:

- ordinal-time Spearman from 2026-07-22 through 2026-08-13: **-0.306373**;
- 17/17 leave-one-day-out trend estimates negative;
- terminal negative run: **9 sessions**;
- July seen-data median Endpoint B: **-0.061330**;
- August seen-data median Endpoint B: **-0.209360**;
- all 9 available August seen sessions negative.

Because this hypothesis was formed after seeing those 17 dates, the temporal-extension test is not evidence that the original drift hypothesis was pre-specified from project inception. Its value comes only from the fact that 2026-07-21 / 20 / 17 remain untouched at the time this protocol is frozen.

## Frozen acquisition scope

For each holdout date use the same construction as the recent opening-validation batches:

- SPXW 0DTE only;
- OPRA TCBBO;
- opening window **09:30-10:00 America/New_York only**;
- opening fitted forward +/- **200 SPX points** exact-symbol strike scope;
- same cached-chain construction and exact-symbol logic;
- same pre-trade NBBO aggressor classifier;
- same M+1 causal feature availability;
- same Black-76 IV/Greek calculations;
- same hedge sign convention;
- same minimum classified-volume Greek coverage: **90%**;
- horizon: **15 minutes only**.

No alternate window, horizon, strike band, coverage floor, aggressor rule, Greek model, sign convention, or call/put split may be introduced after holdout data become visible.

## Frozen primary endpoint

For each untouched date compute exactly:

**Endpoint B:** ordinary Spearman correlation between `hedge_delta_units` and `forward_return_15m_bps` on the frozen 09:30-10:00 / >=90%-coverage sample.

Endpoint A, the historical two-control partial Spearman using `backward_return_1m_bps` and `flow_net_signed_contracts`, may be reported for continuity only. It is not the primary temporal-extension endpoint.

## Frozen temporal-extension adjudication

The drift finding implies that sessions immediately *earlier* than the 2026-07-22 start of the seen chronology should, in aggregate, be **less negative / more positive** than the later August negative cluster if the observed temporal structure extends backward.

Before any holdout inspection, freeze the following descriptive comparisons.

### Primary block comparison

Compute the median Endpoint-B value across the three untouched holdout dates.

Compare it with the already-fixed August seen-data median:

- August reference median = **-0.209360**.

Primary temporal-extension consistency condition:

- holdout 3-day median Endpoint B **> -0.209360**.

Failure condition:

- holdout 3-day median Endpoint B **<= -0.209360**.

This threshold is a frozen descriptive reference to the observed later negative cluster; it is not a fitted trading threshold.

### Secondary sign composition

Report across the three untouched dates:

- negative / positive / exact-zero counts;
- strict sign-stable negative / strict sign-stable positive / sign-fragile counts using the already-frozen leave-one-minute-out category rule.

No minimum positive-day count is required for the primary adjudication. The sign composition is descriptive because three days are too small for a reliable categorical regime estimate.

### Secondary combined chronology

After all three holdout endpoints are revealed, append them before 2026-07-22 in chronological order to form a 20-session series from 2026-07-17 through 2026-08-13.

Report:

- combined 20-session ordinal-time Spearman;
- leave-one-day-out trend sign stability across the 20 sessions;
- fixed 5-session rolling medians using the same already-frozen rolling-window length;
- sign runs.

Interpretation:

- if the combined trend remains negative and the three-date holdout median is above -0.209360, record **temporal-extension support**;
- if the three-date holdout median is <= -0.209360 or the combined trend materially collapses/reverses, record **temporal-extension failure/weakening**;
- mixed evidence must remain mixed and must not be rescued by alternate cutoffs or subwindows.

No p-value or independence claim is authorized.

## Acquisition/reveal discipline

1. Price missing chain-definition/statistics data first using metadata-only calls.
2. Freeze a reviewed metadata cap before any chain purchase.
3. Acquire all required chain inputs for all three dates in the fixed order 2026-07-21, 2026-07-20, 2026-07-17.
4. Price exact-symbol full-day CBBO inputs using metadata-only calls.
5. Freeze a reviewed CBBO cap before any CBBO purchase.
6. Acquire all required CBBO inputs for all three dates before any Endpoint-B result is inspected.
7. Price exact-symbol opening TCBBO for all three dates using metadata-only calls.
8. Freeze per-date reviewed TCBBO caps before any TCBBO purchase.
9. Acquire all three opening TCBBO dates in the fixed order before any endpoint reveal.
10. Prepare all three dates locally without endpoint evaluation.
11. Run safeguards.
12. Reveal the three untouched Endpoint-B values together in one dedicated validator invocation.
13. Record the official holdout result before any influence or post-hoc diagnostic.

No result-driven substitution of dates is permitted.

## Cost rule

No market-data purchase is authorized by this protocol alone.

The next step after protocol freeze is **metadata-only / $0 pricing**. Every paid stage requires a separately reviewed explicit cap based on fresh metadata pricing. Databento guard values are local preflight estimates, not vendor transactional billing caps.

## Scientific limits

This is a three-session untouched temporal-extension block, so it is small and descriptive. The comparison threshold is motivated by the already-seen August cluster and frozen before holdout inspection; it is not an independently derived economic threshold.

The test can strengthen or weaken the temporal-clustering interpretation but cannot establish statistical stationarity, a persistent market regime, causality, or production trading edge.

`hedge_delta_units` remains an inferred opposite-side liquidity-provider/dealer-hedge proxy; OPRA does not identify dealer inventory or executed underlying hedges.
