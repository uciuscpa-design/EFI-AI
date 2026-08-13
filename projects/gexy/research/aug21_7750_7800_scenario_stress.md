# GEXY Aug 21 2026 — 7750 / 7800 Scenario Stress

Reference SPX inferred from matched call/put parity: ~7752.9.

This note uses the previously derived sampled gamma-exposure magnitudes at the two dominant zones only:

- 7750: call ~3.13B, put ~1.12B, unsigned total ~4.25B
- 7800: call ~2.76B, put ~1.24B, unsigned total ~4.00B
- selected-zone unsigned total: ~8.25B
- mixed stress signed total (calls long gamma / puts short gamma): ~3.53B

These are scenario calculations, not claims about actual dealer positioning. Gamma is held at the sampled value and GEX is rescaled by spot^2, matching the project's current first-order scenario implementation.

| Scenario | SPX move | Scenario spot | Signed GEX (B) | Est. hedge demand (B dollar-delta) | Direction |
|---|---:|---:|---:|---:|---|
| long_gamma | -50 | 7702.9 | +8.144 | +5.286 | buy |
| long_gamma | -25 | 7727.9 | +8.197 | +2.652 | buy |
| long_gamma | -10 | 7742.9 | +8.229 | +1.063 | buy |
| long_gamma | +10 | 7762.9 | +8.271 | -1.065 | sell |
| long_gamma | +25 | 7777.9 | +8.303 | -2.669 | sell |
| long_gamma | +50 | 7802.9 | +8.357 | -5.355 | sell |
| short_gamma | -50 | 7702.9 | -8.144 | -5.286 | sell |
| short_gamma | -25 | 7727.9 | -8.197 | -2.652 | sell |
| short_gamma | -10 | 7742.9 | -8.229 | -1.063 | sell |
| short_gamma | +10 | 7762.9 | -8.271 | +1.065 | buy |
| short_gamma | +25 | 7777.9 | -8.303 | +2.669 | buy |
| short_gamma | +50 | 7802.9 | -8.357 | +5.355 | buy |
| mixed | -50 | 7702.9 | +3.485 | +2.262 | buy |
| mixed | -25 | 7727.9 | +3.507 | +1.135 | buy |
| mixed | -10 | 7742.9 | +3.521 | +0.455 | buy |
| mixed | +10 | 7762.9 | +3.539 | -0.456 | sell |
| mixed | +25 | 7777.9 | +3.553 | -1.142 | sell |
| mixed | +50 | 7802.9 | +3.576 | -2.291 | sell |

Interpretation:

- Long-gamma positioning is stabilizing: dealers buy declines and sell rallies.
- Short-gamma positioning is amplifying: dealers sell declines and buy rallies.
- The mixed stress case remains net stabilizing for these two sampled zones because sampled call gamma magnitude materially exceeds put gamma magnitude.
- The hedge-demand figures are first-order model outputs in the project's GEX scaling, not executable flow forecasts. They should be calibrated against observed subsequent SPX returns before being used as predictive magnitudes.
