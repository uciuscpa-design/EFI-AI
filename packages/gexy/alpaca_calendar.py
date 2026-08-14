from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as clock_time
from zoneinfo import ZoneInfo

from .alpaca_provider import AlpacaHttpClient, PAPER_BASE

_ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class AlpacaMarketSession:
    session_date: str
    open_at: datetime
    close_at: datetime

    def contains(self, timestamp: datetime) -> bool:
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        local = timestamp.astimezone(_ET)
        return self.open_at <= local <= self.close_at


def _session_clock(value: object, *, default: str) -> clock_time:
    text = str(value if value not in (None, "") else default)
    return datetime.strptime(text[-5:], "%H:%M").time()


def alpaca_market_session_window(
    timestamp: datetime,
    client: AlpacaHttpClient | None = None,
) -> AlpacaMarketSession | None:
    """Return Alpaca's authoritative regular-session window for timestamp's ET date.

    A missing calendar row means the date is not an Alpaca market session. Open and
    close values come from the calendar itself, so holidays and early closes remain
    authoritative. Returned datetimes are timezone-aware America/New_York values.
    """
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")

    local = timestamp.astimezone(_ET)
    day = local.date().isoformat()
    source = client or AlpacaHttpClient()
    payload = source.get(f"{PAPER_BASE}/v2/calendar", {"start": day, "end": day})
    rows = payload if isinstance(payload, list) else payload.get("calendar", payload.get("days", []))
    if not rows:
        return None

    row = rows[0]
    if str(row.get("date")) != day:
        return None

    open_clock = _session_clock(row.get("open"), default="09:30")
    close_clock = _session_clock(row.get("close"), default="16:00")
    open_at = datetime.combine(local.date(), open_clock, tzinfo=_ET)
    close_at = datetime.combine(local.date(), close_clock, tzinfo=_ET)
    if close_at < open_at:
        raise ValueError("Alpaca calendar close precedes open")

    return AlpacaMarketSession(
        session_date=day,
        open_at=open_at,
        close_at=close_at,
    )


def is_alpaca_market_session(timestamp: datetime, client: AlpacaHttpClient | None = None) -> bool:
    """Return True only while Alpaca's market calendar says the session is open."""
    window = alpaca_market_session_window(timestamp, client)
    return bool(window and window.contains(timestamp))
