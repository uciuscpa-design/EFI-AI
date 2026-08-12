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
    """Persist a feature-engine result without coupling the recorder to the engine model.

    Attribute access is intentionally defensive so this bridge can accept the
    current feature-state model and future compatible models. Missing derived
    fields are recorded as null rather than fabricated.
    """
    recorder.append(
        RecordedSnapshot(
            timestamp=timestamp,
            spot=spot,
            total_gex=getattr(feature_state, "total_gex", None),
            gamma_flip=getattr(feature_state, "gamma_flip", None),
            hedge_demand=getattr(feature_state, "hedge_demand", None),
            positioning_confidence=getattr(feature_state, "positioning_confidence", None),
            data_quality=getattr(feature_state, "data_quality", "unknown"),
            source=source,
        )
    )
