# GEXY Point-in-Time Feature Vector

The feature vector is the contract between normalized market data and the replay/calibration layer.

## Fields
- `timestamp`: source observation time.
- `spot`: SPX price at observation time.
- `es`: optional synchronized ES price.
- `total_gex`: aggregate signed GEX.
- `gamma_flip`: nearest detected gamma sign-change level when available.
- `call_wall`: strongest detected call-side concentration level.
- `put_wall`: strongest detected put-side concentration level.
- `gamma_component`: estimated gamma contribution to hedge pressure.
- `vanna_component`: estimated volatility-sensitivity contribution.
- `charm_component`: estimated time-decay contribution.
- `estimated_hedge_demand`: combined model estimate.
- `hedge_direction`: model-implied direction.
- `positioning_confidence`: explicit confidence in the positioning assumption.

## Point-in-time rule
The builder consumes one synchronized snapshot and supplied option contracts only. It must not access future prices or future option states. Forward outcomes are generated later by the replay layer.

## Modeling limitation
The initial hedge-pressure fields use zero instantaneous price/volatility/time changes because the feature builder represents a static snapshot. Dynamic changes will be supplied by a sequence-aware feature stage once synchronized historical bars and IV-surface changes are available.
