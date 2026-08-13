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

    Hedge-pressure components live on ``feature_state.hedge_pressure``. Missing
    values remain null rather than being inferred so the research log preserves
    exactly what was known at capture time.
    """
    pressure = getattr(feature_state, "hedge_pressure", None)

    recorder.append(
        RecordedSnapshot(
            timestamp=timestamp,
            spot=spot,
            iv=getattr(feature_state, "iv", None),
            total_gex=getattr(feature_state, "total_gex", None),
            total_vanna=getattr(feature_state, "total_vanna", None),
            total_charm=getattr(feature_state, "total_charm", None),
            gamma_flip=getattr(feature_state, "gamma_flip", None),
            gamma_flip_distance=getattr(feature_state, "gamma_flip_distance", None),
            call_wall=getattr(feature_state, "call_wall", None),
            put_wall=getattr(feature_state, "put_wall", None),
            hedge_demand=getattr(pressure, "total_pressure", None) if pressure is not None else None,
            gamma_pressure=getattr(pressure, "gamma_pressure", None) if pressure is not None else None,
            vanna_pressure=getattr(pressure, "vanna_pressure", None) if pressure is not None else None,
            charm_pressure=getattr(pressure, "charm_pressure", None) if pressure is not None else None,
            positioning_confidence=getattr(pressure, "confidence", None) if pressure is not None else None,
            data_quality=getattr(feature_state, "data_quality", "unknown"),
            source=source,
        )
    )
