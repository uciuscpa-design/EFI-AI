from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .calibration import ForecastLabel, make_label
from .recording import RecordedSnapshot


@dataclass(frozen=True)
class SessionResearchRow:
    timestamp: object
    horizon_minutes: int
    spot: float
    spot_change: float
    iv_change: float
    total_gex: float
    gamma_change: float
    total_vanna: float
    total_charm: float
    estimated_hedge_demand: float
    positioning_confidence: float
    gamma_flip_distance: float | None
    regime_score: float = 0.0
    label: ForecastLabel | None = None


def _first_future(records: list[RecordedSnapshot], index: int, horizon_minutes: int) -> RecordedSnapshot | None:
    source = records[index]
    target_time = source.timestamp.timestamp() + horizon_minutes * 60
    for candidate in records[index + 1:]:
        if candidate.timestamp.timestamp() >= target_time:
            return candidate
    return None


def build_session_rows(
    snapshots: Iterable[RecordedSnapshot],
    *,
    horizons_minutes: tuple[int, ...] = (1, 5, 15, 30, 60),
) -> list[SessionResearchRow]:
    """Convert a captured GEXY session into leakage-safe labeled research rows.

    Dynamic features are computed only from the current and immediately prior
    captured observations. Outcomes use the first observation at or after each
    requested future horizon. Rows lacking required feature values are skipped
    rather than forward-filled or fabricated.
    """
    if any(h <= 0 for h in horizons_minutes):
        raise ValueError("horizons must be positive")
    ordered = sorted(snapshots, key=lambda row: row.timestamp)
    result: list[SessionResearchRow] = []

    for i in range(1, len(ordered)):
        previous = ordered[i - 1]
        current = ordered[i]
        required = (
            current.total_gex,
            previous.total_gex,
            current.total_vanna,
            current.total_charm,
            current.hedge_demand,
            current.positioning_confidence,
        )
        if any(value is None for value in required):
            continue
        iv_change = 0.0
        if current.iv is not None and previous.iv is not None:
            iv_change = current.iv - previous.iv

        current_regime = float(current.regime_score) if current.regime_score is not None else 0.0
        for horizon in horizons_minutes:
            future = _first_future(ordered, i, horizon)
            if future is None:
                continue
            result.append(
                SessionResearchRow(
                    timestamp=current.timestamp,
                    horizon_minutes=horizon,
                    spot=current.spot,
                    spot_change=current.spot - previous.spot,
                    iv_change=iv_change,
                    total_gex=float(current.total_gex),
                    gamma_change=float(current.total_gex - previous.total_gex),
                    total_vanna=float(current.total_vanna),
                    total_charm=float(current.total_charm),
                    estimated_hedge_demand=float(current.hedge_demand),
                    positioning_confidence=float(current.positioning_confidence),
                    gamma_flip_distance=current.gamma_flip_distance,
                    regime_score=current_regime,
                    label=make_label(current.spot, future.spot, horizon),
                )
            )
    return result
