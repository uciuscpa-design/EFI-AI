from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class RecordedSnapshot:
    """Point-in-time GEXY research record.

    The recorder stores normalized inputs and derived values together so a
    prediction can be reproduced later. Fields added over time are optional so
    older JSONL experiment files remain readable. Credentials and provider
    secrets must never be included in the payload.
    """

    timestamp: datetime
    spot: float
    iv: float | None = None
    total_gex: float | None = None
    total_vanna: float | None = None
    total_charm: float | None = None
    gamma_flip: float | None = None
    gamma_flip_distance: float | None = None
    call_wall: float | None = None
    put_wall: float | None = None
    hedge_demand: float | None = None
    gamma_pressure: float | None = None
    vanna_pressure: float | None = None
    charm_pressure: float | None = None
    positioning_confidence: float | None = None
    data_quality: str = "unknown"
    source: str = "unknown"


class JsonlRecorder:
    """Small append-only recorder for local research/replay datasets."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, snapshot: RecordedSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(snapshot)
        payload["timestamp"] = snapshot.timestamp.isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    def append_many(self, snapshots: Iterable[RecordedSnapshot]) -> int:
        count = 0
        for snapshot in snapshots:
            self.append(snapshot)
            count += 1
        return count

    def read(self) -> Iterator[RecordedSnapshot]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
                yield RecordedSnapshot(**payload)
