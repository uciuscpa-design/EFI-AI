from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .calibration import CalibrationMetrics, score_forecasts
from .dataset import ResearchRow
from .model import fit_ridge, predict
from .regimes import Regime


@dataclass(frozen=True)
class RegimeResult:
    key: str
    samples: int
    metrics: CalibrationMetrics


def evaluate_by_regime(
    rows: Sequence[ResearchRow],
    regimes: Sequence[Regime],
    *,
    model_builder: Callable = fit_ridge,
    alpha: float = 1.0,
) -> list[RegimeResult]:
    if len(rows) != len(regimes):
        raise ValueError("rows and regimes must have equal length")
    if not rows:
        return []
    model = model_builder(rows, alpha=alpha)
    groups: dict[str, list[int]] = {}
    for i, regime in enumerate(regimes):
        key = f"gamma={regime.gamma}|flip={regime.flip_bucket}|vol={regime.volatility}|0dte={regime.zero_dte}"
        groups.setdefault(key, []).append(i)
    results: list[RegimeResult] = []
    for key, indices in sorted(groups.items()):
        predictions = [predict(model, rows[i]) for i in indices]
        metrics = score_forecasts(
            [p.up_probability for p in predictions],
            [p.move_points for p in predictions],
            [rows[i].label for i in indices],
        )
        results.append(RegimeResult(key, len(indices), metrics))
    return results
