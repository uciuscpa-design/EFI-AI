from __future__ import annotations

from datetime import datetime

from .dataset import ResearchRow
from .feature_engine import GexyFeatureState, build_feature_state
from .market_adapter import MarketSnapshot


def feature_state_to_row(
    state: GexyFeatureState,
    *,
    previous_spot: float = 0.0,
    previous_iv: float | None = None,
) -> ResearchRow:
    """Convert current feature state to the model's live feature schema.

    The label is intentionally neutral because live observations have no future
    outcome yet. Offline evaluation must construct real forward labels.
    """
    spot_change = state.spot - previous_spot if previous_spot else 0.0
    iv_change = (state.iv - previous_iv) if state.iv is not None and previous_iv is not None else 0.0
    return ResearchRow(
        timestamp=state.timestamp,
        spot=state.spot,
        spot_change=spot_change,
        iv_change=iv_change,
        total_gex=state.total_gex,
        gamma_change=0.0,
        vanna_component=state.total_vanna,
        charm_component=state.total_charm,
        estimated_hedge_demand=state.hedge_pressure.total_pressure,
        positioning_confidence=state.hedge_pressure.confidence,
        label=0,
    )


def snapshot_to_row(
    snapshot: MarketSnapshot,
    *,
    previous_spot: float = 0.0,
    previous_iv: float | None = None,
) -> ResearchRow:
    state = build_feature_state(
        snapshot,
        spot_change=snapshot.spot - previous_spot if previous_spot else 0.0,
        iv_change=(snapshot.iv - previous_iv) if snapshot.iv is not None and previous_iv is not None else 0.0,
    )
    return feature_state_to_row(state, previous_spot=previous_spot, previous_iv=previous_iv)
