from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Sequence

from .dataset import ResearchRow


@dataclass(frozen=True)
class ModelPrediction:
    up_probability: float
    move_points: float


@dataclass(frozen=True)
class LinearModel:
    intercept: float
    coefficients: tuple[float, ...]
    mean: tuple[float, ...]
    scale: tuple[float, ...]


def _features(row: ResearchRow) -> tuple[float, ...]:
    return (
        row.total_gex,
        row.gamma_change,
        row.vanna_component,
        row.charm_component,
        row.estimated_hedge_demand,
        row.positioning_confidence,
        row.spot_change,
        row.iv_change,
    )


def fit_ridge(rows: Sequence[ResearchRow], *, alpha: float = 1.0) -> LinearModel:
    if not rows:
        raise ValueError("rows must not be empty")
    if alpha <= 0:
        raise ValueError("alpha must be positive")
    x = [_features(row) for row in rows]
    y = [row.label.return_points for row in rows]
    mean = tuple(sum(row[j] for row in x) / len(x) for j in range(len(x[0])))
    scale = tuple(max(abs(row[j] - mean[j]) for row in x) or 1.0 for j in range(len(x[0])))
    z = [tuple((row[j] - mean[j]) / scale[j] for j in range(len(row))) for row in x]
    # Small dependency-free coordinate descent. Coefficients are standardized and
    # the ridge penalty prevents unstable weights when GEX features are correlated.
    beta = [0.0] * len(z[0])
    intercept = sum(y) / len(y)
    residual = [target - intercept for target in y]
    for _ in range(200):
        for j in range(len(beta)):
            old = beta[j]
            for i in range(len(z)):
                residual[i] += z[i][j] * old
            numerator = sum(z[i][j] * residual[i] for i in range(len(z)))
            denominator = sum(z[i][j] * z[i][j] for i in range(len(z))) + alpha
            beta[j] = numerator / denominator
            for i in range(len(z)):
                residual[i] -= z[i][j] * beta[j]
    return LinearModel(intercept, tuple(beta), mean, scale)


def predict(model: LinearModel, row: ResearchRow) -> ModelPrediction:
    x = _features(row)
    z = [(x[j] - model.mean[j]) / model.scale[j] for j in range(len(x))]
    move = model.intercept + sum(model.coefficients[j] * z[j] for j in range(len(z)))
    probability = 1.0 / (1.0 + exp(-move / max(abs(move), 1.0)))
    return ModelPrediction(probability, move)
