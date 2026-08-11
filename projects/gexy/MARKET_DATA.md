# GEXY Market Data Contract

GEXY separates vendor-specific ingestion from its research/live engine.

## Normalized snapshot
Each point-in-time snapshot contains:
- timestamp
- SPX/underlying spot
- aggregate IV when available
- option-chain records

Each option record may contain:
- symbol
- strike
- expiration
- call/put open interest
- call/put gamma
- call/put vanna
- call/put charm
- implied volatility

## Adapter boundary
Vendor adapters implement `MarketDataAdapter` and yield normalized `MarketSnapshot` objects. The rest of GEXY never depends directly on vendor SDK types.

## Replay first
`ReplayAdapter` implements the same async snapshot interface and is intended for deterministic UI/integration testing before a live market-data provider is selected.

## Live-feed requirements
A production adapter should preserve exchange/vendor timestamps, distinguish quote/trade timestamps, handle stale chains, and expose enough option-level data to reconstruct GEX/Vanna/Charm rather than supplying only pre-aggregated values.
