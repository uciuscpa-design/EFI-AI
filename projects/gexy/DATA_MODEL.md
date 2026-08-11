# GEXY Normalized Market Data Model

## Principle
Provider adapters normalize raw feeds into timestamped immutable records. The mathematical/replay layers consume only normalized records.

## PriceSnapshot
- timestamp
- symbol
- price
- optional volume

Used for SPX and ES.

## OptionSnapshot
- timestamp
- contract_id
- underlying
- strike
- expiration
- option_type
- bid / ask / last
- IV
- delta / gamma / vega / theta
- open interest
- volume
- trade direction when inferable

Missing provider fields remain `None`; they are never fabricated by the normalization layer.

## FeatureSnapshot
A synchronized point-in-time record containing:
- SPX price
- optional ES price
- all option snapshots available at that exact timestamp

## Synchronization rule
The core synchronization function joins records only on exact timestamps. Provider-specific resampling, clock correction, interpolation or nearest-neighbor policies must live in the provider adapter and be documented explicitly.

## Leakage rule
A FeatureSnapshot may contain only information available at or before its timestamp. Forward prices belong exclusively to replay labels.

## Production extension
The live system should eventually support sequence identifiers, source/vendor identifiers, feed timestamps, receive timestamps, quality flags, stale-data flags and market-session metadata.
