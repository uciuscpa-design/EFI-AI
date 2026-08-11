from datetime import datetime, timedelta, timezone

from packages.gexy.provider_normalizer import RawOptionObservation, validate_observation


def make_observation(**kwargs):
    base = dict(
        symbol="SPXW260814C06500000",
        strike=6500,
        expiry=datetime(2026, 8, 14, tzinfo=timezone.utc),
        option_type="C",
        timestamp=datetime(2026, 8, 10, 15, tzinfo=timezone.utc),
        bid=10,
        ask=11,
        open_interest=100,
        implied_volatility=0.2,
    )
    base.update(kwargs)
    return RawOptionObservation(**base)


def test_valid_observation_is_accepted():
    result = validate_observation(make_observation(), now=datetime(2026, 8, 10, 15, 0, 30, tzinfo=timezone.utc))
    assert result.accepted
    assert result.reasons == ()


def test_crossed_quote_is_rejected():
    result = validate_observation(make_observation(bid=12, ask=11))
    assert not result.accepted
    assert "crossed_quote" in result.reasons


def test_stale_observation_is_rejected():
    result = validate_observation(
        make_observation(timestamp=datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)),
        now=datetime(2026, 8, 10, 15, 0, tzinfo=timezone.utc),
    )
    assert not result.accepted
    assert "stale_observation" in result.reasons
