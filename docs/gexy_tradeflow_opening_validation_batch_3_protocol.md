# GEXY opening-window validation batch 3 protocol

## Purpose

Freeze a new untouched validation test for the post-batch time-window hypothesis before pricing or downloading additional TCBBO.

The five-session research set (2026-08-07, 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13) showed that the unchanged net-delta endpoint behaved differently by time of day. This was discovered post-batch and is not itself out-of-sample evidence.

The strongest candidate conditional relationship was the opening-window 15-minute endpoint:

- 5 / 5 research days negative
- median partial Spearman approximately -0.147
- pooled partial Spearman with categorical day fixed effects approximately -0.185

The opening 5-minute endpoint was also negative on 5 / 5 research days but weaker in magnitude and is secondary.

## Untouched validation dates and order

Use the three remaining cached replay/chain sessions that have not had TCBBO trade-flow data inspected:

1. 2026-08-06
2. 2026-08-05
3. 2026-08-04

Do not substitute a different date based on price or expected signal performance. Metadata pricing may determine whether the budget supports all three, but any purchased dates must follow this frozen order and any skipped date must be recorded as a budget decision.

## Frozen data scope

For each purchased validation day use exactly:

- SPXW 0DTE
- TCBBO
- opening flow window only: **09:30-10:00 America/New_York**
- strike scope: opening-forward +/- 200 SPX points
- same exact raw-symbol selection logic
- same frozen pre-trade NBBO aggressor classifier
- same M+1 completed-minute causal availability rule
- same Black-76 forward/IV/delta/gamma calculations
- same 90% classified-volume Greek coverage floor
- same hedge sign convention

The closing window is not purchased for this validation because the candidate rule being tested is explicitly opening-only. This scope is frozen before metadata pricing and before any batch-3 TCBBO is downloaded.

## Primary endpoint

For every validation date, report first:

- opening 15-minute `net_contracts_vs_delta`
- hedge signal: `hedge_delta_units`
- target: 15-minute forward SPX return
- controls:
  1. `backward_return_1m_bps`
  2. `flow_net_signed_contracts`
- statistic: rank-partial Spearman
- expected research-set sign: **negative**

The primary validation question is sign stability on untouched sessions, not whether the magnitude exactly matches the research set.

## Secondary endpoint

Pre-specify, without replacing the primary endpoint:

- opening 5-minute `net_contracts_vs_delta`
- same hedge signal and controls
- expected research-set sign: negative

Because the research-set pooled magnitude was weak, this endpoint is secondary regardless of validation performance.

## Reporting rules

For every purchased date report:

- primary 15m partial Spearman
- secondary 5m partial Spearman
- observations after the 90% Greek-volume coverage floor
- momentum Spearman
- raw-flow partial Spearman controlling momentum
- ordinary hedge Spearman
- hedge partial Spearman controlling momentum
- Greek symbol solve rate
- classified-volume Greek coverage
- replay-match count

After all purchased dates have been processed, report day-level sign stability for the primary endpoint. Do not choose another horizon, call/put component, coverage threshold, strike band, or time sub-window because it performs better.

## Interpretation rule

- Negative primary sign across most or all untouched validation days would strengthen the opening-15m candidate.
- Mixed signs or collapse toward zero would weaken or reject the candidate as a stable conditional relationship.
- A favorable result is still not proof of causality or a production trading edge.
- OPRA does not identify dealer inventory or executed underlying hedge trades; `hedge_delta_units` remains a proxy.

## Cost rule

Before any purchase, run metadata-only pricing for all three frozen dates using the opening window only and the unchanged +/-200-point strike band. Pricing is not validation-result exposure.

Do not download TCBBO during the pricing step. Review the three estimates together before authorizing any paid command.

### Metadata pricing and pre-purchase budget decision — 2026-08-15

Metadata-only pricing was completed for all three frozen batch-3 dates before any batch-3 TCBBO was downloaded or inspected.

Estimated opening-window costs under the unchanged opening-forward +/-200-point selection logic were:

- 2026-08-06: opening forward 7725.886062; 160 exact symbols; **$2.035417**
- 2026-08-05: opening forward 7786.550000; 120 exact symbols; **$1.966996**
- 2026-08-04: opening forward 7636.428480; 136 exact symbols; **$2.315187**
- total estimated batch-3 cost: **$6.317599**

The differing exact-symbol counts arise from applying the same frozen +/-200-point selection logic to each cached chain; the protocol does not require a fixed contract count.

The budget decision is frozen before seeing any batch-3 validation result: purchase **all three dates** in the pre-specified order 2026-08-06, 2026-08-05, 2026-08-04, provided each immediate pre-download re-price remains within its reviewed operational cap. Do not stop early because an intermediate result is favorable or unfavorable, and do not inspect batch-3 endpoint results until all authorized acquisitions are complete.

Reviewed operational caps are:

- 2026-08-06: **$2.08**
- 2026-08-05: **$2.01**
- 2026-08-04: **$2.36**

The downloader's independent absolute safety ceiling remains **$5.00 per invocation**. If any date re-prices above its reviewed operational cap, refuse that download and record a fresh budget review before changing the cap. Any such budget exception must leave the frozen opening-only data scope and endpoint definitions unchanged.

### Acquisition record — 2026-08-06

The first batch-3 opening-window date was purchased on 2026-08-15 before any batch-3 trade-flow extraction, Greek weighting, feature scoring, or endpoint analysis was performed.

The immediate pre-download re-price remained **$2.035417**, within the frozen **$2.08** operational cap. The unchanged 160-symbol 09:30-10:00 America/New_York TCBBO window was cached successfully.

No 2026-08-06 batch-3 endpoint result has been inspected. The batch remains committed to continue in the frozen order with 2026-08-05 and then 2026-08-04 before any batch-3 extraction or validation analysis. No early stopping is permitted based on intermediate results.

### Acquisition record — 2026-08-05

The second batch-3 opening-window date was purchased on 2026-08-15 before any batch-3 trade-flow extraction, Greek weighting, feature scoring, or endpoint analysis was performed.

The immediate pre-download re-price remained **$1.966996**, within the frozen **$2.01** operational cap. The unchanged 120-symbol 09:30-10:00 America/New_York TCBBO window was cached successfully.

No 2026-08-06 or 2026-08-05 batch-3 endpoint result has been inspected. The batch remains committed to purchase the final frozen date, 2026-08-04, before any batch-3 extraction or validation analysis. No early stopping is permitted based on intermediate results.
