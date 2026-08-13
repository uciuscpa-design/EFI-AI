from __future__ import annotations

from datetime import datetime
from typing import Any

from .recording import JsonlRecorder, RecordedSnapshot


def record_feature_state(
    recorder: JsonlRecorder,
    *,
    timestamp: datetime,
    spot: float,
    feature_state: Any,
    source: str = "alpaca",
) -> None:
    """Persist a feature-engine result into the canonical research recorder.

    Hedge demand and confidence live on ``feature_state.hedge_pressure`` in the
    current feature model. Missing values remain null rather than being inferred.
    """
    pressure = getattr(feature_state, "hedge_pressure", None)
    hedge_demand = getattr(pressure, "total_pressure", None) if pressure is not None else None
    positioning_confidence = getattr(pressure, "confidence", None) if pressure is not None else None

    recorder.append(
        RecordedSnapshot(
            timestamp=timestamp,
            spot=spot,
            total_gex=getattr(feature_state, "total_gex", None),
            gamma_flip=getattr(feature_state, "gamma_flip", None),
            hedge_demand=hedge_demand,
            positioning_confidence=positioning_confidence,
            data_quality=getattr(feature_state, "data_quality", "unknown"),
            source=source,
        )
    )
