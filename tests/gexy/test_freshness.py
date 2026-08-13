from datetime import datetime, timedelta, timezone

import pytest

from packages.gexy.freshness import validate_snapshot_freshness


def test_accepts_recent_quote() -> None:
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)
    result = validate_snapshot_freshness(
        observation_time=now,
        quote_time=now - timedelta(seconds=20),
        max_age_seconds=90,
    )
    assert result.fresh is True
    assert result.reason == "fresh"


def test_rejects_stale_quote() -> None:
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)
    result = validate_snapshot_freshness(
        observation_time=now,
        quote_time=now - timedelta(minutes=5),
        max_age_seconds=90,
    )
    assert result.fresh is False
    assert result.reason == "quote is stale"


def test_rejects_future_quote() -> None:
    now = datetime(2026, 8, 13, 14, 30, tzinfo=timezone.utc)
    result = validate_snapshot_freshness(
        observation_time=now,
        quote_time=now + timedelta(seconds=1),
    )
    assert result.fresh is False
    assert result.reason == "quote timestamp is in the future"


def test_requires_aware_timestamps() -> None:
    now = datetime(2026, 8, 13, 14, 30)
    with pytest.raises(ValueError, match="timezone-aware"):
        validate_snapshot_freshness(observation_time=now, quote_time=now)
