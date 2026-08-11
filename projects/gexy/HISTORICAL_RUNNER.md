# GEXY Historical Runner

The historical runner combines normalized option snapshots with strictly later SPX observations.

For every timestamp it records the positioning state available at that time and pairs the forecast with a future price change at the requested horizon.

## No-lookahead rules
- Features use only the current snapshot.
- Forward labels use observations strictly after the prediction timestamp.
- Training, validation, and test periods remain chronological.
- Model and threshold selection must occur before the locked test period.

The runner is infrastructure for empirical testing; it does not imply that GEX, dealer hedging, or any particular options-flow mechanism is predictive until measured on out-of-sample data.
