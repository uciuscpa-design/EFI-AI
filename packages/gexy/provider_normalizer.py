from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RawOptionObservation:
    symbol: str
    strike: float
    expiry: datetime
    option_type: str
    timestamp: datetime
    bid: float | None = None
    ask: float | None = None
    trade: float | None = None
    open_interest: float | None = None
    implied_volatility: float | None = None
    gamma: float | None = None
    vanna: float | None = None
    charm: float | None = None


@dataclass(frozen=True)
class QualityResult:
    accepted: bool
    reasons: tuple[str, ...]


def validate_observation(
    observation: RawOptionObservation,
    *,
    now: datetime | None = None,
    max_age_seconds: float = 120.0,
) -> QualityResult:
    reasons: list[str] = []
    if observation.option_type.upper() not in {"C", "P", "CALL", "PUT"}:
        reasons.append("invalid_option_type")
    if observation.strike <= 0:
        reasons.append("invalid_strike")
    if observation.expiry.tzinfo is None:
        reasons.append("expiry_must_be_timezone_aware")
    if observation.timestamp.tzinfo is None:
        reasons.append("timestamp_must_be_timezone_aware")
    if observation.bid is not None and observation.ask is not None:
        if observation.bid < 0 or observation.ask < 0:
            reasons.append("negative_quote")
        if observation.bid > observation.ask:
            reasons.append("crossed_quote")
    if observation.open_interest is not None and observation.open_interest < 0:
        reasons.append("negative_open_interest")
    if observation.implied_volatility is not None and observation.implied_volatility < 0:
        reasons.append("negative_iv")
    if observation.timestamp.tzinfo is not None and now is not None:
        age = (now - observation.timestamp).total_seconds()
        if age < -5:
            reasons.append("future_timestamp")
        elif age > max_age_seconds:
            reasons.append("stale_observation")
    return QualityResult(not reasons, tuple(reasons))


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)
