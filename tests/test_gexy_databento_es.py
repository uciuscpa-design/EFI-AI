from datetime import datetime, timedelta, timezone

import pytest

from packages.gexy.databento_es import (
    DEFAULT_DATABENTO_CONTINUOUS_SYMBOL,
    DEFAULT_DATABENTO_DATASET,
    DEFAULT_DATABENTO_SCHEMA,
    DEFAULT_DATABENTO_STYPE_IN,
    DatabentoEsConfig,
    DatabentoSymbolMapping,
    DatabentoTradeEvent,
    event_provenance_record,
    market_observation_from_trade,
    validate_symbol_mapping,
)
from packages.gexy.market_sync import datetime_to_unix_ns


def _ns(value: datetime) -> int:
    return datetime_to_unix_ns(value)


def _event(*, raw_symbol: str = "ESU6", instrument_id: int = 12345) -> DatabentoTradeEvent:
    event_at = datetime(2026, 8, 17, 13, 30, 0, 100000, tzinfo=timezone.utc)
    provider_recv = event_at + timedelta(milliseconds=2)
    return DatabentoTradeEvent(
        instrument_id=instrument_id,
        raw_symbol=raw_symbol,
        price_nanos=7_787_250_000_000,
        ts_event_ns=_ns(event_at),
        ts_recv_ns=_ns(provider_recv),
        publisher_id=1,
    )


def _mapping(*, raw_symbol: str = "ESU6", instrument_id: int = 12345) -> DatabentoSymbolMapping:
    return DatabentoSymbolMapping(
        continuous_symbol="ES.v.0",
        raw_symbol=raw_symbol,
        instrument_id=instrument_id,
        mapped_at=datetime(2026, 8, 17, 13, 29, 59, tzinfo=timezone.utc),
    )


def test_frozen_databento_es_config_targets_cme_globex_es_continuous_trade_stream():
    config = DatabentoEsConfig()
    assert config.dataset == DEFAULT_DATABENTO_DATASET == "GLBX.MDP3"
    assert config.schema == DEFAULT_DATABENTO_SCHEMA == "trades"
    assert config.continuous_symbol == DEFAULT_DATABENTO_CONTINUOUS_SYMBOL == "ES.v.0"
    assert config.stype_in == DEFAULT_DATABENTO_STYPE_IN == "continuous"


def test_trade_event_preserves_event_and_provider_receive_timestamps_separately():
    event = _event()

    assert event.price == 7787.25
    assert event.observed_at == datetime(2026, 8, 17, 13, 30, 0, 100000, tzinfo=timezone.utc)
    assert event.provider_received_at == datetime(2026, 8, 17, 13, 30, 0, 102000, tzinfo=timezone.utc)
    assert event.provider_capture_latency_seconds == pytest.approx(0.002)


def test_submicrosecond_vendor_timestamp_survives_datetime_projection():
    event_at = datetime(2026, 8, 17, 13, 30, 0, 100000, tzinfo=timezone.utc)
    base_ns = _ns(event_at)
    event = DatabentoTradeEvent(
        instrument_id=12345,
        raw_symbol="ESU6",
        price_nanos=7_787_250_000_000,
        ts_event_ns=base_ns + 777,
        ts_recv_ns=base_ns + 2_000_777,
        publisher_id=1,
    )

    assert event.observed_at == event_at
    assert event.ts_event_ns == base_ns + 777
    assert event.provider_capture_latency_seconds == pytest.approx(0.002)


def test_mapped_trade_becomes_provider_neutral_market_observation():
    event = _event()
    mapping = _mapping()
    gexy_received_at = datetime(2026, 8, 17, 13, 30, 0, 105000, tzinfo=timezone.utc)

    observation = market_observation_from_trade(
        event,
        gexy_received_at=gexy_received_at,
        mapping=mapping,
    )

    assert observation.symbol == "ESU6"
    assert observation.instrument_type == "future"
    assert observation.price == 7787.25
    assert observation.observed_at == event.observed_at
    assert observation.event_time_ns == event.ts_event_ns
    assert observation.received_at == gexy_received_at
    assert observation.source == "databento:GLBX.MDP3:publisher=1"
    assert observation.acquisition_latency_seconds == pytest.approx(0.005)


def test_future_symbol_mapping_is_rejected_as_lookahead():
    event = _event()
    mapping = DatabentoSymbolMapping(
        continuous_symbol="ES.v.0",
        raw_symbol="ESU6",
        instrument_id=12345,
        mapped_at=event.observed_at + timedelta(microseconds=1),
    )

    with pytest.raises(ValueError, match="mapping is from the future"):
        validate_symbol_mapping(event, mapping)


def test_mismatched_raw_symbol_or_instrument_id_is_rejected():
    event = _event()

    with pytest.raises(ValueError, match="raw symbol mapping mismatch"):
        validate_symbol_mapping(event, _mapping(raw_symbol="ESZ6"))

    with pytest.raises(ValueError, match="instrument_id mapping mismatch"):
        validate_symbol_mapping(event, _mapping(instrument_id=99999))


def test_event_provenance_record_contains_roll_identity_and_vendor_timestamps():
    event = _event()

    record = event_provenance_record(event)

    assert record["provider"] == "databento"
    assert record["dataset"] == "GLBX.MDP3"
    assert record["schema"] == "trades"
    assert record["continuous_symbol"] == "ES.v.0"
    assert record["raw_symbol"] == "ESU6"
    assert record["instrument_id"] == 12345
    assert record["publisher_id"] == 1
    assert record["price"] == 7787.25
    assert record["ts_event_ns"] == event.ts_event_ns
    assert record["ts_recv_ns"] == event.ts_recv_ns
    assert record["ts_event"] == "2026-08-17T13:30:00.100000+00:00"
    assert record["ts_recv"] == "2026-08-17T13:30:00.102000+00:00"


def test_trade_event_rejects_invalid_identity_price_or_timestamps():
    base = dict(
        instrument_id=12345,
        raw_symbol="ESU6",
        price_nanos=7_787_250_000_000,
        ts_event_ns=1,
        ts_recv_ns=2,
    )

    with pytest.raises(ValueError, match="instrument_id must be positive"):
        DatabentoTradeEvent(**{**base, "instrument_id": 0})
    with pytest.raises(ValueError, match="raw_symbol must not be empty"):
        DatabentoTradeEvent(**{**base, "raw_symbol": ""})
    with pytest.raises(ValueError, match="price_nanos must be positive"):
        DatabentoTradeEvent(**{**base, "price_nanos": 0})
    with pytest.raises(ValueError, match="ts_event_ns must be positive"):
        DatabentoTradeEvent(**{**base, "ts_event_ns": 0})
    with pytest.raises(ValueError, match="ts_recv_ns must be >= ts_event_ns"):
        DatabentoTradeEvent(**{**base, "ts_event_ns": 3, "ts_recv_ns": 2})
