from datetime import datetime, timedelta, timezone

import pytest

from packages.gexy.market_sync import (
    MarketObservation,
    latest_at_or_before,
    pair_to_record,
    synchronize_primary_with_reference,
    synchronize_series,
)


def _observation(
    symbol: str,
    *,
    seconds: float,
    price: float,
    instrument_type: str,
    received_delay_seconds: float = 0.25,
    source: str = "test-provider",
) -> MarketObservation:
    base = datetime(2026, 8, 17, 13, 30, tzinfo=timezone.utc)
    observed_at = base + timedelta(seconds=seconds)
    return MarketObservation(
        symbol=symbol,
        instrument_type=instrument_type,
        price=price,
        observed_at=observed_at,
        received_at=observed_at + timedelta(seconds=received_delay_seconds),
        source=source,
    )


def test_latest_at_or_before_never_selects_closer_future_reference():
    primary = _observation("SPX", seconds=10.0, price=7600.0, instrument_type="cash_index")
    references = [
        _observation("ESU6", seconds=9.0, price=7610.0, instrument_type="future"),
        _observation("ESU6", seconds=10.1, price=7611.0, instrument_type="future"),
    ]

    selected = latest_at_or_before(references, anchor_at=primary.observed_at)

    assert selected is not None
    assert selected.observed_at == references[0].observed_at
    assert selected.price == 7610.0


def test_exact_timestamp_match_is_scoreable():
    primary = _observation("SPX", seconds=10.0, price=7600.0, instrument_type="cash_index")
    reference = _observation("ESU6", seconds=10.0, price=7610.0, instrument_type="future")

    pair = synchronize_primary_with_reference(primary, [reference], max_lag_seconds=2.0)

    assert pair.status == "matched"
    assert pair.reference_lag_seconds == 0.0
    assert pair.scoreable is True
    assert pair.no_lookahead_enforced is True


def test_stale_reference_is_retained_for_diagnostics_but_unscoreable():
    primary = _observation("SPX", seconds=10.0, price=7600.0, instrument_type="cash_index")
    reference = _observation("ESU6", seconds=4.0, price=7608.0, instrument_type="future")

    pair = synchronize_primary_with_reference(primary, [reference], max_lag_seconds=5.0)

    assert pair.status == "stale_reference"
    assert pair.reference is reference
    assert pair.reference_lag_seconds == 6.0
    assert pair.scoreable is False


def test_future_only_reference_set_is_missing_not_backfilled_from_future():
    primary = _observation("SPX", seconds=10.0, price=7600.0, instrument_type="cash_index")
    future_reference = _observation("ESU6", seconds=10.001, price=7610.0, instrument_type="future")

    pair = synchronize_primary_with_reference(primary, [future_reference], max_lag_seconds=5.0)

    assert pair.status == "missing_reference"
    assert pair.reference is None
    assert pair.reference_lag_seconds is None
    assert pair.scoreable is False


def test_series_join_preserves_no_lookahead_for_each_primary():
    primaries = [
        _observation("SPX", seconds=5.0, price=7599.0, instrument_type="cash_index"),
        _observation("SPX", seconds=10.0, price=7600.0, instrument_type="cash_index"),
    ]
    references = [
        _observation("ESU6", seconds=4.0, price=7608.0, instrument_type="future"),
        _observation("ESU6", seconds=9.0, price=7610.0, instrument_type="future"),
        _observation("ESU6", seconds=11.0, price=7612.0, instrument_type="future"),
    ]

    pairs = synchronize_series(primaries, references, max_lag_seconds=2.0)

    assert [pair.reference.price for pair in pairs if pair.reference is not None] == [7608.0, 7610.0]
    assert all(pair.scoreable for pair in pairs)
    assert all(pair.reference.observed_at <= pair.primary.observed_at for pair in pairs if pair.reference)


def test_serialized_record_preserves_source_and_event_vs_receive_timestamps():
    primary = _observation(
        "SPX",
        seconds=10.0,
        price=7600.0,
        instrument_type="cash_index",
        received_delay_seconds=0.4,
        source="spx-provider",
    )
    reference = _observation(
        "ESU6",
        seconds=9.5,
        price=7610.0,
        instrument_type="future",
        received_delay_seconds=0.7,
        source="es-provider",
    )

    record = pair_to_record(
        synchronize_primary_with_reference(primary, [reference], max_lag_seconds=2.0)
    )

    assert record["status"] == "matched"
    assert record["no_lookahead_enforced"] is True
    assert record["primary"]["source"] == "spx-provider"
    assert record["reference"]["source"] == "es-provider"
    assert record["primary"]["observed_at"] != record["primary"]["received_at"]
    assert record["reference"]["observed_at"] != record["reference"]["received_at"]


def test_observation_and_sync_parameters_reject_invalid_time_or_lag():
    naive = datetime(2026, 8, 17, 13, 30)
    aware = naive.replace(tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="observed_at must be timezone-aware"):
        MarketObservation(
            symbol="SPX",
            instrument_type="cash_index",
            price=7600.0,
            observed_at=naive,
            received_at=aware,
            source="test",
        )

    primary = _observation("SPX", seconds=0.0, price=7600.0, instrument_type="cash_index")
    with pytest.raises(ValueError, match="max_lag_seconds must be non-negative"):
        synchronize_primary_with_reference(primary, [], max_lag_seconds=-0.1)
