# GEXY Live Forecast Engine

The live path is intentionally separated from research/training.

## Flow
`live SPX/ES + options adapters -> normalized snapshot -> dynamic feature row -> pre-fitted horizon models -> forecast response -> chart overlay`

## Forecast response
Each horizon returns:
- timestamp
- current SPX spot
- predicted move in SPX points
- probability of an upward move
- confidence score

## Initial horizons
1m, 5m, 15m, 30m, 60m.

## Safety boundary
The live forecast service never trains, recalibrates, or consumes future observations. Model fitting happens offline. A deployment must load versioned models and record their training period/version with every forecast stream.

## Chart contract
The frontend can render each forecast as a future price band centered on current spot, with direction encoded by the predicted move and uncertainty/confidence controlling the visual envelope. The exact overlay should remain adjustable by the user.

## Next implementation
Add a FastAPI endpoint and websocket/SSE stream, then connect real market-data adapters. The first live endpoint should support synthetic/replay snapshots so UI development can proceed before a paid market-data feed is selected.
