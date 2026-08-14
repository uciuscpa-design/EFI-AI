from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from .alpaca_provider import AlpacaHttpClient, PAPER_BASE

_ET = ZoneInfo("America/New_York")


def is_alpaca_market_session(timestamp: datetime, client: AlpacaHttpClient | None = None) -> bool:
    """Return True only while Alpaca's market calendar says the session is open.

    This handles holidays and early closes. The timestamp must be timezone-aware.
    """
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    local = timestamp.astimezone(_ET)
    day = local.date().isoformat()
    source = client or AlpacaHttpClient()
    payload = source.get(f"{PAPER_BASE}/v2/calendar", {"start": day, "end": day})
    rows = payload if isinstance(payload, list) else payload.get("calendar", payload.get("days", []))
    if not rows:
        return False

    row = rows[0]
    if str(row.get("date")) != day:
        return False

    open_text = str(row.get("open", "09:30"))
    close_text = str(row.get("close", "16:00"))
    open_clock = datetime.strptime(open_text[-5:], "%H:%M").time()
    close_clock = datetime.strptime(close_text[-5:], "%H:%M").time()
    clock = local.time().replace(tzinfo=None)
    return open_clock <= clock <= close_clock
