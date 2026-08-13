from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .gax_features import GAXFeatures
from .prediction_journal import PredictionJournalEntry


@dataclass(frozen=True)
class GAXShadowRecord:
    prediction_id: str
    created_at: datetime
    horizon_minutes: int
    model_version: str
    features: GAXFeatures


@dataclass(frozen=True)
class GAXShadowMetrics:
    resolved: int
    bias_alignment_accuracy: float
    mean_magnitude: float
    mean_absolute_curvature: float


def make_gax_shadow_record(
    *,
    prediction_id: str,
    created_at: datetime,
    horizon_minutes: int,
    model_version: str,
    features: GAXFeatures,
) -> GAXShadowRecord:
    if not prediction_id.strip():
        raise ValueError("prediction_id must not be empty")
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be positive")
    if not model_version.strip():
        raise ValueError("model_version must not be empty")
    return GAXShadowRecord(
        prediction_id=prediction_id,
        created_at=created_at,
        horizon_minutes=horizon_minutes,
        model_version=model_version.strip(),
        features=features,
    )


def _serialize(record: GAXShadowRecord) -> dict[str, object]:
    payload = asdict(record)
    payload["created_at"] = record.created_at.isoformat()
    return payload


def _deserialize(payload: dict[str, object]) -> GAXShadowRecord:
    features = payload.get("features")
    if not isinstance(features, dict):
        raise ValueError("features must be an object")
    return GAXShadowRecord(
        prediction_id=str(payload["prediction_id"]),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        horizon_minutes=int(payload["horizon_minutes"]),
        model_version=str(payload["model_version"]),
        features=GAXFeatures(**features),
    )


def append_gax_shadow(path: str | Path, record: GAXShadowRecord) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_serialize(record), sort_keys=True) + "\n")


def load_gax_shadows(path: str | Path) -> list[GAXShadowRecord]:
    target = Path(path)
    if not target.exists():
        return []
    records: list[GAXShadowRecord] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(_deserialize(json.loads(line)))
    return records


def index_gax_shadows(records: Iterable[GAXShadowRecord]) -> dict[str, GAXShadowRecord]:
    return {record.prediction_id: record for record in records}


def summarize_gax_shadow(
    entries: Iterable[PredictionJournalEntry],
    shadows: Iterable[GAXShadowRecord],
) -> GAXShadowMetrics:
    shadow_index = index_gax_shadows(shadows)
    paired = [
        (entry, shadow_index[entry.prediction_id])
        for entry in entries
        if entry.resolved and entry.prediction_id in shadow_index
    ]
    if not paired:
        return GAXShadowMetrics(0, 0.0, 0.0, 0.0)

    def aligned(entry: PredictionJournalEntry, shadow: GAXShadowRecord) -> bool:
        move = float(entry.realized_move_points or 0.0)
        bias = shadow.features.acceleration_bias
        if bias == "up":
            return move > 0
        if bias == "down":
            return move < 0
        return abs(move) < 1e-9

    return GAXShadowMetrics(
        resolved=len(paired),
        bias_alignment_accuracy=sum(aligned(entry, shadow) for entry, shadow in paired) / len(paired),
        mean_magnitude=sum(shadow.features.magnitude for _, shadow in paired) / len(paired),
        mean_absolute_curvature=sum(abs(shadow.features.local_gax_curvature) for _, shadow in paired) / len(paired),
    )
