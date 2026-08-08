from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor: str
    payload: dict[str, Any]
    timestamp: datetime


class AuditLog:
    """Process-local audit sink; replace with durable storage in the next persistence phase."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, event_type: str, payload: dict[str, Any], actor: str = "system") -> AuditEvent:
        event = AuditEvent(event_type, actor, payload, datetime.now(timezone.utc))
        self._events.append(event)
        return event

    def recent(self, limit: int = 100) -> list[AuditEvent]:
        return self._events[-limit:]
