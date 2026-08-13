from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .gax_features import GAXFeatures


@dataclass(frozen=True)
class GAXShadowRecord:
    prediction_id: str
    created_at: datetime
    horizon_minutes: int
    model_version: str
    features: GAXFeatures


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
