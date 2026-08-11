from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HedgePressure:
    gamma_pressure: float
    vanna_pressure: float
    charm_pressure: float
    total_pressure: float
    confidence: float


def estimate_hedge_pressure(
    *,
    total_gex: float,
    total_vanna: float,
    total_charm: float,
    spot_change: float,
    iv_change: float,
    dt_minutes: float = 1.0,
) -> HedgePressure:
    """Compute an explicit pressure feature, not a claim of actual dealer flow.

    Coefficients are intentionally transparent placeholders. They must be fitted
    and validated against historical data before being used for live prediction.
    """
    if dt_minutes <= 0:
        raise ValueError("dt_minutes must be positive")
    gamma = total_gex * spot_change
    vanna = total_vanna * iv_change
    charm = total_charm / dt_minutes
    total = gamma + vanna + charm
    confidence = min(1.0, abs(total) / (1.0 + abs(gamma) + abs(vanna) + abs(charm)))
    return HedgePressure(gamma, vanna, charm, total, confidence)
