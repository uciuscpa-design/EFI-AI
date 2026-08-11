from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .backtest import BacktestPoint, chronological_points
from .feature_engine import build_feature_state
from .market_adapter import MarketSnapshot


@dataclass(frozen=True)
class HistoricalPoint:
    timestamp: object
    spot: float
    total_gex: float
    total_vanna: float
    total_charm: float
    gamma_flip: float | None
    predicted_move: float
    actual_move: float | None


def build_historical_points(
    snapshots: Sequence[MarketSnapshot],
    predicted_moves: Sequence[float],
    *,
    horizon_steps: int,
    horizon_minutes: int,
) -> list[HistoricalPoint]:
    if len(snapshots) != len(predicted_moves):
        raise ValueError("snapshots and predictions must have equal length")
    base: list[BacktestPoint] = chronological_points(
        snapshots,
        predicted_moves,
        horizon_steps=horizon_steps,
        horizon_minutes=horizon_minutes,
    )
    by_timestamp = {p.timestamp: p for p in base}
    result: list[HistoricalPoint] = []
    for snapshot in snapshots:
        point = by_timestamp.get(snapshot.timestamp)
        if point is None:
            continue
        state = build_feature_state(snapshot)
        result.append(
            HistoricalPoint(
                timestamp=snapshot.timestamp,
                spot=snapshot.spot,
                total_gex=state.total_gex,
                total_vanna=state.total_vanna,
                total_charm=state.total_charm,
                gamma_flip=state.gamma_flip,
                predicted_move=point.predicted_move,
                actual_move=point.actual_move,
            )
        )
    return result
