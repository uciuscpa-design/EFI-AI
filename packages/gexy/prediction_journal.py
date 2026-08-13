from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .live_prediction import LivePrediction


LIVE_MODEL_VERSION = "gexy-live-v1"


@dataclass(frozen=True)
class PredictionJournalEntry:
    prediction_id: str
    created_at: datetime
    spot: float
    prediction: LivePrediction
    model_version: str = LIVE_MODEL_VERSION
    resolved_at: datetime | None = None
    realized_spot: float | None = None
    realized_move_points: float | None = None
    directional_hit: bool | None = None
    absolute_error_points: float | None = None

    @property
    def due_at(self) -> datetime:
        return self.created_at + timedelta(minutes=self.prediction.horizon_minutes)

    @property
    def resolved(self) -> bool:
        return self.resolved_at is not None


def _prediction_id(
    created_at: datetime,
    spot: float,
    prediction: LivePrediction,
    model_version: str,
) -> str:
    stamp = created_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    direction = prediction.direction.lower()
    return f"{stamp}-{spot:.2f}-{prediction.horizon_minutes}m-{direction}-{model_version}"


def make_entry(
    *,
    created_at: datetime,
    spot: float,
    prediction: LivePrediction,
    model_version: str = LIVE_MODEL_VERSION,
) -> PredictionJournalEntry:
    if created_at.tzinfo is None:
        raise ValueError('created_at must be timezone-aware')
    if spot <= 0:
        raise ValueError('spot must be positive')
    version = model_version.strip()
    if not version:
        raise ValueError('model_version must not be empty')
    return PredictionJournalEntry(
        prediction_id=_prediction_id(created_at, spot, prediction, version),
        created_at=created_at,
        spot=float(spot),
        prediction=prediction,
        model_version=version,
    )


def _serialize(entry: PredictionJournalEntry) -> dict[str, object]:
    payload = asdict(entry)
    payload['created_at'] = entry.created_at.isoformat()
    payload['resolved_at'] = None if entry.resolved_at is None else entry.resolved_at.isoformat()
    return payload


def _deserialize(payload: dict[str, object]) -> PredictionJournalEntry:
    prediction_payload = payload['prediction']
    if not isinstance(prediction_payload, dict):
        raise ValueError('prediction must be an object')
    return PredictionJournalEntry(
        prediction_id=str(payload['prediction_id']),
        created_at=datetime.fromisoformat(str(payload['created_at'])),
        spot=float(payload['spot']),
        prediction=LivePrediction(**prediction_payload),
        model_version=str(payload.get('model_version') or LIVE_MODEL_VERSION),
        resolved_at=None if payload.get('resolved_at') is None else datetime.fromisoformat(str(payload['resolved_at'])),
        realized_spot=None if payload.get('realized_spot') is None else float(payload['realized_spot']),
        realized_move_points=None if payload.get('realized_move_points') is None else float(payload['realized_move_points']),
        directional_hit=None if payload.get('directional_hit') is None else bool(payload['directional_hit']),
        absolute_error_points=None if payload.get('absolute_error_points') is None else float(payload['absolute_error_points']),
    )


def append_entry(path: str | Path, entry: PredictionJournalEntry) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(_serialize(entry), sort_keys=True) + '\n')


def load_entries(path: str | Path) -> list[PredictionJournalEntry]:
    target = Path(path)
    if not target.exists():
        return []
    entries: list[PredictionJournalEntry] = []
    for line in target.read_text(encoding='utf-8').splitlines():
        if line.strip():
            entries.append(_deserialize(json.loads(line)))
    return entries


def resolve_entry(entry: PredictionJournalEntry, *, resolved_at: datetime, realized_spot: float) -> PredictionJournalEntry:
    if entry.resolved:
        return entry
    if resolved_at.tzinfo is None:
        raise ValueError('resolved_at must be timezone-aware')
    if resolved_at < entry.due_at:
        raise ValueError('prediction horizon has not elapsed')
    if realized_spot <= 0:
        raise ValueError('realized_spot must be positive')
    realized_move = float(realized_spot - entry.spot)
    direction = entry.prediction.direction
    if direction == 'up':
        hit = realized_move > 0
    elif direction == 'down':
        hit = realized_move < 0
    else:
        hit = abs(realized_move) < 1e-9
    error = abs(entry.prediction.expected_move_points - realized_move)
    return PredictionJournalEntry(
        prediction_id=entry.prediction_id,
        created_at=entry.created_at,
        spot=entry.spot,
        prediction=entry.prediction,
        model_version=entry.model_version,
        resolved_at=resolved_at,
        realized_spot=float(realized_spot),
        realized_move_points=realized_move,
        directional_hit=hit,
        absolute_error_points=error,
    )


def rewrite_entries(path: str | Path, entries: Iterable[PredictionJournalEntry]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('w', encoding='utf-8') as handle:
        for entry in entries:
            handle.write(json.dumps(_serialize(entry), sort_keys=True) + '\n')


@dataclass(frozen=True)
class JournalSummary:
    total: int
    resolved: int
    pending: int
    directional_accuracy: float
    mean_absolute_error_points: float
    mean_confidence: float


def summarize_entries(entries: Iterable[PredictionJournalEntry]) -> JournalSummary:
    rows = list(entries)
    resolved = [entry for entry in rows if entry.resolved]
    if resolved:
        accuracy = sum(bool(entry.directional_hit) for entry in resolved) / len(resolved)
        mae = sum(float(entry.absolute_error_points or 0.0) for entry in resolved) / len(resolved)
        confidence = sum(entry.prediction.confidence for entry in resolved) / len(resolved)
    else:
        accuracy = 0.0
        mae = 0.0
        confidence = 0.0
    return JournalSummary(
        total=len(rows),
        resolved=len(resolved),
        pending=len(rows) - len(resolved),
        directional_accuracy=accuracy,
        mean_absolute_error_points=mae,
        mean_confidence=confidence,
    )
