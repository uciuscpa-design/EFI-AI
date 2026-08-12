from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class GexySnapshot:
    timestamp: datetime
    spot: float
    total_gex: float | None
    gamma_flip: float | None
    hedge_demand: float | None
    positioning_confidence: float
    data_quality: str
    source: str


class GexyRecorder:
    """Append-only recorder for point-in-time GEXY research observations."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, snapshot: GexySnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = asdict(snapshot)
        payload["timestamp"] = snapshot.timestamp.isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    def read(self) -> list[GexySnapshot]:
        if not self.path.exists():
            return []
        result: list[GexySnapshot] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
                result.append(GexySnapshot(**payload))
        return result
