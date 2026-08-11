# GEXY Regime Analysis

GEXY will evaluate predictive performance conditional on market structure rather than relying only on aggregate scores.

## Dimensions
- Gamma sign: positive / negative / neutral
- Distance from gamma flip: near / above / below / unknown
- Implied-volatility regime: low / normal / high / unknown
- 0DTE flag: true / false

## Gamma flip distance
The initial bucket treats a move within 0.1% of spot (with a minimum one SPX point) as near the flip. This is a research threshold, not a universal market constant; it should be optimized on validation data only.

## Volatility buckets
The initial thresholds are IV < 15%, 15–25%, and >=25%. These are deliberately simple baseline buckets and must not be presented as empirically optimal until validated.

## Future extensions
- liquidity/spread regime
- realized-volatility regime
- opening/closing-session regime
- days-to-expiration buckets
- option concentration / wall proximity
- ES/SPX basis regime

All regime definitions must be available at the prediction timestamp and must not use future outcomes.
