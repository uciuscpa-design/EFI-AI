from datetime import datetime, timezone

from packages.gexy.market_session import is_regular_spx_cash_session


def test_regular_spx_cash_session_boundaries() -> None:
    assert is_regular_spx_cash_session(datetime(2026, 8, 14, 13, 29, tzinfo=timezone.utc)) is False
    assert is_regular_spx_cash_session(datetime(2026, 8, 14, 13, 30, tzinfo=timezone.utc)) is True
    assert is_regular_spx_cash_session(datetime(2026, 8, 14, 19, 59, tzinfo=timezone.utc)) is True
    assert is_regular_spx_cash_session(datetime(2026, 8, 14, 20, 1, tzinfo=timezone.utc)) is False


def test_weekend_is_not_regular_spx_cash_session() -> None:
    assert is_regular_spx_cash_session(datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)) is False
