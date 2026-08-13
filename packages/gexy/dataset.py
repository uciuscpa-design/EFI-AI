from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .calibration import ForecastLabel, make_label
from .dynamic_features import DynamicFeatureRow
from .replay import MarketSnapshot, build_forward_labels
from .regime import regime_score


@dataclass(frozen=True)
class ResearchRow:
    timestamp: datetime
    spot: float
    spot_change: float
    iv_change: float
    total_gex: float
    gamma_change: float
    vanna_component: float
    charm_component: float
    estimated_hedge_demand: float
    positioning_confidence: float
    label: ForecastLabel
    regime_score: float = 0.0


def assemble_rows(
    features: Iterable[DynamicFeatureRow],
    prices: Iterable[MarketSnapshot],
    *,
    horizon_minutes: int,
) -> list[ResearchRow]:
    """Join point-in-time features to future price labels by timestamp.

    Features are never shifted forward or filled from future observations. A row
    is emitted only when a source feature timestamp has an eligible future price.
    """
    feature_rows = sorted(features, key=lambda row: row.timestamp)
    price_rows = sorted(prices, key=lambda row: row.timestamp)
    labels = build_forward_labels(price_rows, horizon_minutes=horizon_minutes)
    label_by_time = {sample.snapshot.timestamp: sample.label for sample in labels}
    result: list[ResearchRow] = []
    for feature in feature_rows:
        label = label_by_time.get(feature.timestamp)
        if label is None:
            continue
        regime = regime_score(
            signed_gex=feature.total_gex,
            spot_change=feature.spot_change,
            confidence=feature.positioning_confidence,
        )
        result.append(
            ResearchRow(
                timestamp=feature.timestamp,
                spot=feature.spot,
                spot_change=feature.spot_change,
                iv_change=feature.iv_change,
                total_gex=feature.total_gex,
                gamma_change=feature.gamma_change,
                vanna_component=feature.vanna_component,
                charm_component=feature.charm_component,
                estimated_hedge_demand=feature.estimated_hedge_demand,
                positioning_confidence=feature.positioning_confidence,
                label=label,
                regime_score=regime.score,
            )
        )
    return result
