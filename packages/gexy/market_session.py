from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")
_OPEN = time(9, 30)
_CLOSE = time(16, 0)


def is_regular_spx_cash_session(timestamp: datetime) -> bool:
    """Return True only during the weekday 09:30-16:00 America/New_York cash session.

    This is a conservative scoring guard, not an exchange-calendar implementation.
    Holiday/early-close awareness can be layered on later via Alpaca's calendar.
    """
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    local = timestamp.astimezone(_ET)
    if local.weekday() >= 5:
        return False
    clock = local.time().replace(tzinfo=None)
    return _OPEN <= clock <= _CLOSE
