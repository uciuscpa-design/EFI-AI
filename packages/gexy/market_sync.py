from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


def datetime_to_unix_ns(value: datetime) -> int:
    """Convert an aware datetime to exact integer Unix nanoseconds.

    Python datetime is microsecond-resolution, so this conversion never routes
    through floating point. Providers with finer timestamps can additionally set
    `observed_at_ns` on MarketObservation to preserve their raw event ordering.
    """
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    delta = value.astimezone(timezone.utc) - _EPOCH_UTC
    return (
        (delta.days * 86_400 + delta.seconds) * 1_000_000_000
        + delta.microseconds * 1_000
    )


@dataclass(frozen=True)
class MarketObservation:
    """One provider-timestamped market observation.

    `observed_at` is a human-readable provider/event timestamp.
    `observed_at_ns` optionally preserves a provider's finer raw Unix-nanosecond
    timestamp. Point-in-time joins use `event_time_ns`, not datetime comparison,
    so a reference even one nanosecond after the anchor is never accepted.

    `received_at` is when GEXY acquired the observation. Event and acquisition
    time are preserved independently so latency can be audited.
    """

    symbol: str
    instrument_type: str
    price: float
    observed_at: datetime
    received_at: datetime
    source: str
    observed_at_ns: int | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not self.instrument_type.strip():
            raise ValueError("instrument_type must not be empty")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if self.observed_at_ns is not None:
            if self.observed_at_ns <= 0:
                raise ValueError("observed_at_ns must be positive")
            # The datetime projection may lose sub-microsecond precision, but it
            # must still represent the same Unix microsecond as the raw ns value.
            if self.observed_at_ns // 1_000 != datetime_to_unix_ns(self.observed_at) // 1_000:
                raise ValueError("observed_at_ns is inconsistent with observed_at")

    @property
    def event_time_ns(self) -> int:
        return self.observed_at_ns if self.observed_at_ns is not None else datetime_to_unix_ns(self.observed_at)

    @property
    def received_time_ns(self) -> int:
        return datetime_to_unix_ns(self.received_at)

    @property
    def acquisition_latency_seconds(self) -> float:
        return (self.received_time_ns - self.event_time_ns) / 1_000_000_000


@dataclass(frozen=True)
class SynchronizedMarketPair:
    """Point-in-time pair anchored on a primary market observation.

    The reference observation is always at-or-before the primary event timestamp.
    A future reference is never selected, including a reference that differs only
    at sub-microsecond precision. Stale matches are retained for diagnostics but
    remain unscoreable.
    """

    primary: MarketObservation
    reference: MarketObservation | None
    max_lag_seconds: float
    status: str
    reference_lag_seconds: float | None
    scoreable: bool
    no_lookahead_enforced: bool = True


def inferred_spot_observation(
    *,
    symbol: str,
    price: float,
    source_quote_times: Iterable[datetime],
    received_at: datetime,
    source: str,
    instrument_type: str = "cash_index_inferred",
) -> MarketObservation:
    """Create an inferred spot observation at the first safe information time.

    If a synthetic value depends on multiple source quotes, the value does not
    exist point-in-time until the latest required quote has occurred. Using the
    latest source event timestamp prevents an earlier anchor from leaking one of
    the inputs used to construct the inferred spot.
    """
    quote_times = tuple(source_quote_times)
    if not quote_times:
        raise ValueError("source_quote_times must not be empty")
    if any(value.tzinfo is None for value in quote_times):
        raise ValueError("source_quote_times must be timezone-aware")
    safe_anchor = max(quote_times)
    return MarketObservation(
        symbol=symbol,
        instrument_type=instrument_type,
        price=price,
        observed_at=safe_anchor,
        received_at=received_at,
        source=source,
        observed_at_ns=datetime_to_unix_ns(safe_anchor),
    )


def _validate_max_lag(max_lag_seconds: float) -> None:
    if max_lag_seconds < 0:
        raise ValueError("max_lag_seconds must be non-negative")


def latest_at_or_before(
    observations: Iterable[MarketObservation],
    *,
    anchor_at: datetime,
    anchor_at_ns: int | None = None,
) -> MarketObservation | None:
    """Return the latest observation whose exact event time is <= the anchor.

    No interpolation and no nearest-neighbor search are used because either could
    accidentally consume a later observation during historical replay.
    """
    if anchor_at.tzinfo is None:
        raise ValueError("anchor_at must be timezone-aware")
    anchor_ns = datetime_to_unix_ns(anchor_at) if anchor_at_ns is None else int(anchor_at_ns)
    if anchor_ns <= 0:
        raise ValueError("anchor_at_ns must be positive")
    if anchor_ns // 1_000 != datetime_to_unix_ns(anchor_at) // 1_000:
        raise ValueError("anchor_at_ns is inconsistent with anchor_at")

    eligible = [observation for observation in observations if observation.event_time_ns <= anchor_ns]
    if not eligible:
        return None
    return max(eligible, key=lambda observation: observation.event_time_ns)


def synchronize_primary_with_reference(
    primary: MarketObservation,
    references: Iterable[MarketObservation],
    *,
    max_lag_seconds: float = 5.0,
) -> SynchronizedMarketPair:
    """Synchronize one primary event with the latest non-future reference event."""
    _validate_max_lag(max_lag_seconds)
    reference = latest_at_or_before(
        references,
        anchor_at=primary.observed_at,
        anchor_at_ns=primary.event_time_ns,
    )
    if reference is None:
        return SynchronizedMarketPair(
            primary=primary,
            reference=None,
            max_lag_seconds=max_lag_seconds,
            status="missing_reference",
            reference_lag_seconds=None,
            scoreable=False,
        )

    lag_ns = primary.event_time_ns - reference.event_time_ns
    lag_seconds = lag_ns / 1_000_000_000
    if lag_seconds > max_lag_seconds:
        return SynchronizedMarketPair(
            primary=primary,
            reference=reference,
            max_lag_seconds=max_lag_seconds,
            status="stale_reference",
            reference_lag_seconds=lag_seconds,
            scoreable=False,
        )

    return SynchronizedMarketPair(
        primary=primary,
        reference=reference,
        max_lag_seconds=max_lag_seconds,
        status="matched",
        reference_lag_seconds=lag_seconds,
        scoreable=True,
    )


def synchronize_series(
    primaries: Iterable[MarketObservation],
    references: Iterable[MarketObservation],
    *,
    max_lag_seconds: float = 5.0,
) -> tuple[SynchronizedMarketPair, ...]:
    """Synchronize a chronological primary series without future-data leakage."""
    _validate_max_lag(max_lag_seconds)
    reference_rows = tuple(references)
    return tuple(
        synchronize_primary_with_reference(
            primary,
            reference_rows,
            max_lag_seconds=max_lag_seconds,
        )
        for primary in primaries
    )


def _observation_record(observation: MarketObservation) -> dict[str, object]:
    return {
        "symbol": observation.symbol,
        "instrument_type": observation.instrument_type,
        "price": observation.price,
        "observed_at": observation.observed_at.isoformat(),
        "observed_at_ns": observation.event_time_ns,
        "received_at": observation.received_at.isoformat(),
        "source": observation.source,
        "acquisition_latency_seconds": observation.acquisition_latency_seconds,
    }


def pair_to_record(pair: SynchronizedMarketPair) -> dict[str, object]:
    """Serialize a sync result while preserving provenance and exact event order."""
    return {
        "status": pair.status,
        "scoreable": pair.scoreable,
        "no_lookahead_enforced": pair.no_lookahead_enforced,
        "max_lag_seconds": pair.max_lag_seconds,
        "reference_lag_seconds": pair.reference_lag_seconds,
        "primary": _observation_record(pair.primary),
        "reference": None if pair.reference is None else _observation_record(pair.reference),
    }
