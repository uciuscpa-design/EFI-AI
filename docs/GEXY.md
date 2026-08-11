# GEXY — SPX Gamma Exposure Research

## Purpose

GEXY is the research and visualization layer for estimating SPX/SPXW option gamma exposure and the resulting dealer hedge-pressure response. It is a research system, not a claim that market-maker inventory can be observed directly from open interest.

## Data-quality rules

- Provider Greeks are preferred when available.
- When Greeks/IV are absent, GEXY may derive IV from a synchronized option midpoint and derive Black-Scholes gamma.
- Open interest is treated as a lagged input unless the provider supplies an intraday OI update.
- Missing OI is not silently converted into zero; callers should reduce `oi_confidence`.
- SPX and SPXW are aggregated by the underlying but remain separate contract records.
- No forward-move prediction is emitted until historical calibration and synchronized underlying data are available.
- The UI should display `INSUFFICIENT DATA` instead of fabricating a signal.

## Exposure convention

For a contract, the common 1% gamma-exposure magnitude is:

`gamma * open_interest * multiplier * spot^2 * 0.01`

The engine exposes two explicit positioning scenarios:

- `dealer_long_gamma`: positive gamma exposure.
- `dealer_short_gamma`: negative gamma exposure.
- `mixed`: neutral placeholder until an inventory model is supplied.

For a delta-neutral dealer, incremental hedge demand is represented as `-GEX * dS`: positive dealer gamma tends to hedge against the move, while negative dealer gamma tends to reinforce it.

## API

`POST /v1/gexy/surface`

The endpoint accepts a reference SPX price, positioning scenario, price-grid parameters, and normalized option records. It returns the GEX curve, hedge-pressure sensitivity, candidate gamma flip, wall locations, and a data-quality score.

## Roadmap

1. Validate the deterministic exposure engine.
2. Build an Alpaca ingestion adapter for normalized SPX/SPXW option records.
3. Add synchronized SPX/SPY underlying and option timestamps.
4. Persist exposure snapshots for replay.
5. Add historical labels for 1m/5m/15m/30m/60m forward returns.
6. Calibrate and score a probabilistic UP/FLAT/DOWN model.
7. Build the standalone adjustable candle/GEX overlay window.
8. Add live monitoring with a hard data-quality gate.

## Current limitation

The connected Alpaca environment currently exposes indicative option data but does not provide OPRA access. GEXY therefore keeps the data source and quality state explicit and does not represent indicative data as consolidated OPRA data.
