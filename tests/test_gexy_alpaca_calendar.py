from datetime import datetime, timezone

from packages.gexy.alpaca_calendar import is_alpaca_market_session


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, params=None):
        return self.payload


def test_normal_session_is_open():
    client = FakeClient([{"date": "2026-08-14", "open": "09:30", "close": "16:00"}])
    ts = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)  # 10:00 ET
    assert is_alpaca_market_session(ts, client) is True


def test_holiday_is_closed():
    client = FakeClient([])
    ts = datetime(2026, 12, 25, 15, 0, tzinfo=timezone.utc)
    assert is_alpaca_market_session(ts, client) is False


def test_early_close_is_respected():
    client = FakeClient([{"date": "2026-11-27", "open": "09:30", "close": "13:00"}])
    before_close = datetime(2026, 11, 27, 17, 30, tzinfo=timezone.utc)  # 12:30 ET
    after_close = datetime(2026, 11, 27, 18, 30, tzinfo=timezone.utc)   # 13:30 ET
    assert is_alpaca_market_session(before_close, client) is True
    assert is_alpaca_market_session(after_close, client) is False
