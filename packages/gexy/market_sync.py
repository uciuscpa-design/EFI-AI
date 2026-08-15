from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class MarketObservation:
    """One provider-timestamped market observation.

    `observed_at` is the provider/event timestamp used for point-in-time joins.
    `received_at` is when GEXY acquired the observation. Both are preserved so
    latency can be audited instead of silently collapsed into one timestamp.
    """

    symbol: str
    instrument_type: str
    price: float
    observed_at: datetime
    received_at: datetime
    source: str

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

    @property
    def acquisition_latency_seconds(self) -> float:
        return (self.received_at - self.observed_at).total_seconds()


@dataclass(frozen=True)
class SynchronizedMarketPair:
    """Point-in-time pair anchored on a primary market observation.

    The reference observation is always at-or-before the primary event timestamp.
    A future reference is never selected, which makes the join safe for replay and
    forward validation. Stale matches are retained for diagnostics but unscoreable.
    """

    primary: MarketObservation
    reference: MarketObservation | None
    max_lag_seconds: float
    status: str
    reference_lag_seconds: float | None
    scoreable: bool
    no_lookahead_enforced: bool = True


def _validate_max_lag(max_lag_seconds: float) -> None:
    if max_lag_seconds < 0:
        raise ValueError("max_lag_seconds must be non-negative")


def latest_at_or_before(
    observations: Iterable[MarketObservation],
    *,
    anchor_at: datetime,
) -> MarketObservation | None:
    """Return the latest observation whose event time is <= `anchor_at`.

    No interpolation and no nearest-neighbor search are used because either could
    accidentally consume a later observation during historical replay.
    """
    if anchor_at.tzinfo is None:
        raise ValueError("anchor_at must be timezone-aware")
    eligible = [observation for observation in observations if observation.observed_at <= anchor_at]
    if not eligible:
        return None
    return max(eligible, key=lambda observation: observation.observed_at)


def synchronize_primary_with_reference(
    primary: MarketObservation,
    references: Iterable[MarketObservation],
    *,
    max_lag_seconds: float = 5.0,
) -> SynchronizedMarketPair:
    """Synchronize one primary event with the latest non-future reference event."""
    _validate_max_lag(max_lag_seconds)
    reference = latest_at_or_before(references, anchor_at=primary.observed_at)
    if reference is None:
        return SynchronizedMarketPair(
            primary=primary,
            reference=None,
            max_lag_seconds=max_lag_seconds,
            status="missing_reference",
            reference_lag_seconds=None,
            scoreable=False,
        )

    lag_seconds = (primary.observed_at - reference.observed_at).total_seconds()
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


def pair_to_record(pair: SynchronizedMarketPair) -> dict[str, object]:
    """Serialize a sync result while preserving provenance and both timestamps."""
    primary = pair.primary
    reference = pair.reference
    return {
        "status": pair.status,
        "scoreable": pair.scoreable,
        "no_lookahead_enforced": pair.no_lookahead_enforced,
        "max_lag_seconds": pair.max_lag_seconds,
        "reference_lag_seconds": pair.reference_lag_seconds,
        "primary": {
            "symbol": primary.symbol,
            "instrument_type": primary.instrument_type,
            "price": primary.price,
            "observed_at": primary.observed_at.isoformat(),
            "received_at": primary.received_at.isoformat(),
            "source": primary.source,
            "acquisition_latency_seconds": primary.acquisition_latency_seconds,
        },
        "reference": None
        if reference is None
        else {
            "symbol": reference.symbol,
            "instrument_type": reference.instrument_type,
            "price": reference.price,
            "observed_at": reference.observed_at.isoformat(),
            "received_at": reference.received_at.isoformat(),
            "source": reference.source,
            "acquisition_latency_seconds": reference.acquisition_latency_seconds,
        },
    }
