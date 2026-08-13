# GEXY Experiment 001 — Aug 21 Surface Rank

Connected Alpaca indicative SPX chain, 2026-08-12 close. Quotes timestamped ~19:59:59 UTC. Alpaca indicative feed returned no IV/Greeks, so IV and gamma were derived from Black-Scholes using matched call/put parity with an inferred SPX reference near 7752.9 and ~9 calendar days to expiry. Open interest is Alpaca contract metadata dated 2026-08-10.

Important: these are unsigned gamma-exposure magnitudes, not claims about dealer long/short inventory.

| Strike | Call IV | Put IV | Call gamma | Put gamma | Call GEX magnitude | Put GEX magnitude | Combined magnitude |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 7700 | 10.24% | 10.26% | 0.002912 | 0.002909 | $2.257B | $0.919B | $3.176B |
| 7750 | 9.47% | 9.45% | 0.003460 | 0.003466 | $3.135B | $1.119B | $4.254B |
| 7775 | 9.23% | 9.21% | 0.003487 | 0.003494 | $2.213B | $0.104B | $2.317B |
| 7800 | 9.23% | 9.28% | 0.003263 | 0.003249 | $2.766B | $1.234B | $4.000B |

## Rank

1. 7750 — strongest sampled gamma-magnitude zone.
2. 7800 — second strongest sampled zone.
3. 7700 — third strongest sampled zone.
4. 7775 — strong call concentration but much smaller put-side magnitude.

## Interpretation constraint

Do not treat this ordering as resistance/support or a directional forecast. Direction requires an explicit dealer-position hypothesis or observed flow signal. This file is a structural sensitivity map only.
