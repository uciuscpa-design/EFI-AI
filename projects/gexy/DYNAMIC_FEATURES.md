# GEXY Dynamic Feature Layer

The dynamic layer converts point-in-time GEXY states into sequence-aware research features.

## Features
- SPX point change
- implied-volatility change
- elapsed time
- total GEX
- GEX change
- Vanna component
- Charm component
- estimated hedge demand
- positioning confidence

## Intended relationship
For a dealer delta estimate D:

`ΔD ≈ Gamma·ΔS + Vanna·ΔIV + Charm·Δt`

Estimated hedge demand is modeled with the opposite sign:

`ΔH ≈ -ΔD`

The dynamic feature row stores the observable changes and the model-derived hedge-demand estimate separately.

## Important limitation
A single scalar `total_gex` is not sufficient to recover the full dealer book. GEXY will retain strike-level features and scenario surfaces alongside these sequence features as the model develops.

## No-lookahead rule
All fields in a dynamic row must be computable using data available at the row timestamp. Forward SPX prices are labels only and never features.
