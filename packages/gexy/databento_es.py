from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .market_sync import MarketObservation, datetime_to_unix_ns


DEFAULT_DATABENTO_DATASET = "GLBX.MDP3"
DEFAULT_DATABENTO_SCHEMA = "trades"
DEFAULT_DATABENTO_CONTINUOUS_SYMBOL = "ES.v.0"
DEFAULT_DATABENTO_STYPE_IN = "continuous"
_DATABENTO_FIXED_PRICE_SCALE = 1_000_000_000
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _datetime_from_unix_ns(value: int) -> datetime:
    """Project integer Unix nanoseconds to Python's microsecond datetime exactly.

    The raw integer remains the source of truth for event ordering. This helper is
    only the human-readable projection and never routes through floating point.
    """
    if value <= 0:
        raise ValueError("Unix nanoseconds must be positive")
    seconds, remainder_ns = divmod(value, 1_000_000_000)
    return _EPOCH_UTC + timedelta(seconds=seconds, microseconds=remainder_ns // 1_000)


@dataclass(frozen=True)
class DatabentoEsConfig:
    """Frozen research configuration for the first ES market-data adapter.

    Networking is intentionally outside this module. The boundary accepts vendor
    records only after authentication/subscription succeeds elsewhere, keeping
    credentials out of the normalization and synchronization layers.
    """

    dataset: str = DEFAULT_DATABENTO_DATASET
    schema: str = DEFAULT_DATABENTO_SCHEMA
    continuous_symbol: str = DEFAULT_DATABENTO_CONTINUOUS_SYMBOL
    stype_in: str = DEFAULT_DATABENTO_STYPE_IN


@dataclass(frozen=True)
class DatabentoSymbolMapping:
    """Point-in-time mapping from a smart ES symbol to an actual CME contract."""

    continuous_symbol: str
    raw_symbol: str
    instrument_id: int
    mapped_at: datetime

    def __post_init__(self) -> None:
        if not self.continuous_symbol.strip():
            raise ValueError("continuous_symbol must not be empty")
        if not self.raw_symbol.strip():
            raise ValueError("raw_symbol must not be empty")
        if self.instrument_id <= 0:
            raise ValueError("instrument_id must be positive")
        if self.mapped_at.tzinfo is None:
            raise ValueError("mapped_at must be timezone-aware")


@dataclass(frozen=True)
class DatabentoTradeEvent:
    """Normalized subset of a Databento `trades` record required by GEXY.

    Databento DBN prices are fixed-point integers where one unit is 1e-9. Event
    and receive timestamps are retained independently as nanoseconds from Unix
    epoch. The raw contract symbol comes from a contemporaneous symbol mapping.
    """

    instrument_id: int
    raw_symbol: str
    price_nanos: int
    ts_event_ns: int
    ts_recv_ns: int
    publisher_id: int | None = None
    dataset: str = DEFAULT_DATABENTO_DATASET
    continuous_symbol: str = DEFAULT_DATABENTO_CONTINUOUS_SYMBOL

    def __post_init__(self) -> None:
        if self.instrument_id <= 0:
            raise ValueError("instrument_id must be positive")
        if not self.raw_symbol.strip():
            raise ValueError("raw_symbol must not be empty")
        if self.price_nanos <= 0:
            raise ValueError("price_nanos must be positive")
        if self.ts_event_ns <= 0:
            raise ValueError("ts_event_ns must be positive")
        if self.ts_recv_ns <= 0:
            raise ValueError("ts_recv_ns must be positive")
        if self.ts_recv_ns < self.ts_event_ns:
            raise ValueError("ts_recv_ns must be >= ts_event_ns")
        if not self.dataset.strip():
            raise ValueError("dataset must not be empty")
        if not self.continuous_symbol.strip():
            raise ValueError("continuous_symbol must not be empty")

    @property
    def price(self) -> float:
        return self.price_nanos / _DATABENTO_FIXED_PRICE_SCALE

    @property
    def observed_at(self) -> datetime:
        return _datetime_from_unix_ns(self.ts_event_ns)

    @property
    def provider_received_at(self) -> datetime:
        return _datetime_from_unix_ns(self.ts_recv_ns)

    @property
    def provider_capture_latency_seconds(self) -> float:
        return (self.ts_recv_ns - self.ts_event_ns) / 1_000_000_000


def validate_symbol_mapping(
    event: DatabentoTradeEvent,
    mapping: DatabentoSymbolMapping,
) -> None:
    """Refuse to attach a trade to an ES contract through a mismatched mapping."""
    if mapping.continuous_symbol != event.continuous_symbol:
        raise ValueError("continuous symbol mapping mismatch")
    if mapping.raw_symbol != event.raw_symbol:
        raise ValueError("raw symbol mapping mismatch")
    if mapping.instrument_id != event.instrument_id:
        raise ValueError("instrument_id mapping mismatch")
    if datetime_to_unix_ns(mapping.mapped_at) > event.ts_event_ns:
        raise ValueError("symbol mapping is from the future relative to the event")


def market_observation_from_trade(
    event: DatabentoTradeEvent,
    *,
    gexy_received_at: datetime,
    mapping: DatabentoSymbolMapping | None = None,
) -> MarketObservation:
    """Convert a mapped ES trade into GEXY's provider-neutral observation.

    `observed_at` is the microsecond projection of CME/Databento event time while
    `observed_at_ns` retains the exact vendor nanoseconds used for point-in-time
    ordering. `received_at` is when GEXY received/processed the record, not
    Databento's capture time. Vendor `ts_recv` remains on DatabentoTradeEvent for
    provider-latency diagnostics.
    """
    if gexy_received_at.tzinfo is None:
        raise ValueError("gexy_received_at must be timezone-aware")
    if mapping is not None:
        validate_symbol_mapping(event, mapping)

    publisher = "unknown" if event.publisher_id is None else str(event.publisher_id)
    return MarketObservation(
        symbol=event.raw_symbol,
        instrument_type="future",
        price=event.price,
        observed_at=event.observed_at,
        observed_at_ns=event.ts_event_ns,
        received_at=gexy_received_at,
        source=f"databento:{event.dataset}:publisher={publisher}",
    )


def event_provenance_record(event: DatabentoTradeEvent) -> dict[str, object]:
    """Serialize Databento-specific provenance that should accompany sync data."""
    return {
        "provider": "databento",
        "dataset": event.dataset,
        "schema": DEFAULT_DATABENTO_SCHEMA,
        "continuous_symbol": event.continuous_symbol,
        "raw_symbol": event.raw_symbol,
        "instrument_id": event.instrument_id,
        "publisher_id": event.publisher_id,
        "price": event.price,
        "price_nanos": event.price_nanos,
        "ts_event_ns": event.ts_event_ns,
        "ts_recv_ns": event.ts_recv_ns,
        "ts_event": event.observed_at.isoformat(),
        "ts_recv": event.provider_received_at.isoformat(),
        "provider_capture_latency_seconds": event.provider_capture_latency_seconds,
    }
