from datetime import datetime, timezone

from packages.gexy.alpaca_calendar import alpaca_market_session_window, is_alpaca_market_session


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        return self.payload


def test_normal_session_is_open_and_window_is_timezone_aware():
    client = FakeClient([{"date": "2026-08-14", "open": "09:30", "close": "16:00"}])
    ts = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)  # 10:00 ET

    window = alpaca_market_session_window(ts, client)

    assert window is not None
    assert window.session_date == "2026-08-14"
    assert window.open_at.isoformat() == "2026-08-14T09:30:00-04:00"
    assert window.close_at.isoformat() == "2026-08-14T16:00:00-04:00"
    assert window.open_at.tzinfo is not None
    assert window.close_at.tzinfo is not None
    assert window.contains(ts) is True
    assert client.calls[0][1] == {"start": "2026-08-14", "end": "2026-08-14"}


def test_normal_session_boolean_wrapper_is_open():
    client = FakeClient([{"date": "2026-08-14", "open": "09:30", "close": "16:00"}])
    ts = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)  # 10:00 ET
    assert is_alpaca_market_session(ts, client) is True


def test_holiday_has_no_session_window_and_is_closed():
    client = FakeClient([])
    ts = datetime(2026, 12, 25, 15, 0, tzinfo=timezone.utc)
    assert alpaca_market_session_window(ts, client) is None
    assert is_alpaca_market_session(ts, client) is False


def test_mismatched_calendar_date_has_no_session_window():
    client = FakeClient([{"date": "2026-08-13", "open": "09:30", "close": "16:00"}])
    ts = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)
    assert alpaca_market_session_window(ts, client) is None


def test_early_close_is_respected_and_exposed_by_window():
    client = FakeClient([{"date": "2026-11-27", "open": "09:30", "close": "13:00"}])
    before_close = datetime(2026, 11, 27, 17, 30, tzinfo=timezone.utc)  # 12:30 ET
    after_close = datetime(2026, 11, 27, 18, 30, tzinfo=timezone.utc)   # 13:30 ET

    window = alpaca_market_session_window(before_close, client)

    assert window is not None
    assert window.close_at.isoformat() == "2026-11-27T13:00:00-05:00"
    assert window.contains(before_close) is True
    assert window.contains(after_close) is False
    assert is_alpaca_market_session(before_close, client) is True
    assert is_alpaca_market_session(after_close, client) is False


def test_timestamp_must_be_timezone_aware():
    client = FakeClient([])
    naive = datetime(2026, 8, 14, 10, 0)

    try:
        alpaca_market_session_window(naive, client)
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_window_contains_rejects_naive_timestamp():
    client = FakeClient([{"date": "2026-08-14", "open": "09:30", "close": "16:00"}])
    window = alpaca_market_session_window(datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc), client)
    assert window is not None

    try:
        window.contains(datetime(2026, 8, 14, 10, 0))
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_invalid_calendar_window_rejected():
    client = FakeClient([{"date": "2026-08-14", "open": "16:00", "close": "09:30"}])
    ts = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)

    try:
        alpaca_market_session_window(ts, client)
    except ValueError as exc:
        assert "close precedes open" in str(exc)
    else:
        raise AssertionError("expected ValueError")
