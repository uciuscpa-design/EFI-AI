# gexy Status

Last updated: 2026-08-14

## Objective

gexy is the SPX/SPXW options analytics track inside EFI-AI. The immediate goal is to build a trustworthy market-data and gamma-exposure foundation before adding prediction, chart overlays, backtesting, or execution-adjacent logic.

## Live-data findings

- Alpaca authentication/connectivity is working. A live SPY stock snapshot was retrieved successfully.
- SPX option contract discovery works and returns SPXW European-style contracts with strike, expiration, contract multiplier, and open interest.
- Individual SPXW indicative snapshots return current option trades and quotes.
- The current Alpaca account does not have OPRA entitlement; OPRA requests return `subscription does not permit querying OPRA data`.
- Indicative snapshots tested for both 0DTE SPXW contracts and the next SPXW expiry returned `null` implied volatility and Greeks.
- Alpaca's stock snapshot path did not return an SPX index snapshot, so gexy must use a separate SPX spot source or another explicitly validated spot mechanism. SPY must not be silently substituted as SPX.

## Architecture decisions

### Separate options domain

The existing `packages/data/market.py` quote boundary remains generic. gexy options logic lives in its own domain under `packages/options` with an Alpaca adapter under `packages/data/alpaca_options.py`.

### IV and gamma fallback

Because the indicative feed cannot currently be relied on to return IV/Greeks, gexy includes European Black-Scholes pricing, implied-volatility solving, and gamma calculation. These functions require an explicit SPX spot, time to expiry, risk-free rate, and dividend yield rather than inventing hidden defaults in the orchestration layer.

### GEX convention

Contract gamma exposure for a 1% underlying move is represented as:

`gamma * open_interest * multiplier * spot^2 * 0.01 * sign`

Two sign modes are supported:

- `unsigned`: no directional sign assumption.
- `call_put_proxy`: calls are positive and puts are negative.

`call_put_proxy` is intentionally labeled a heuristic. Open interest does not reveal dealer/customer direction, so this metric must not be described as observed dealer gamma positioning.

### GAX

No GAX formula is being invented. GAX remains gated until its exact project definition is recovered or explicitly defined and testable.

## Current branch

`agent/gexy-options-foundation`

The branch currently contains:

- `packages/options/models.py`
- `packages/options/greeks.py`
- `packages/options/gex.py`
- `packages/options/__init__.py`
- `packages/data/alpaca_options.py`
- `tests/test_gexy_options.py`
- Alpaca environment settings and safe `.env.example` placeholders

## Next gates

1. Full repository CI must pass.
2. Add a validated SPX spot provider boundary and at least one real source.
3. Build a gexy orchestration service that joins contract metadata, option marks, spot, IV, gamma, and GEX.
4. Persist raw inputs plus calculation assumptions so every GEX snapshot is reproducible.
5. Expose read-only gexy API endpoints only after the above layer is deterministic and tested.
6. Add historical replay/backtesting and then prediction features.
7. Add GAX only after its exact formula and sign semantics are defined.
