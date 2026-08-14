from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Callable, Iterable, Sequence
from zoneinfo import ZoneInfo

from .prediction_journal import PredictionJournalEntry, load_entries

_ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class FeatureObservation:
    timestamp: datetime
    spot: float
    local_gex: float | None
    local_gex_slope: float | None
    hedge_acceleration: float | None
    distance_to_flip: float | None
    distance_to_lower_wall: float | None
    distance_to_upper_wall: float | None
    spot_momentum_points: float | None = None

    @property
    def et_minute(self) -> float:
        local = self.timestamp.astimezone(_ET)
        return float(local.hour * 60 + local.minute) + local.second / 60.0


@dataclass(frozen=True)
class JoinedShadowRow:
    entry: PredictionJournalEntry
    observation: FeatureObservation


FeatureGetter = Callable[[FeatureObservation], float | None]
Rule = Callable[[JoinedShadowRow], str | None]


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _utc_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def load_feature_observations(paths: Iterable[str | Path]) -> list[FeatureObservation]:
    """Reconstruct live GEX surface observations from session collector JSON logs.

    The session collector emits one JSON object per cycle. Successful cycles retain
    the exact live-predict timestamp, spot and surface feature payload that produced
    the shadow journal entries, allowing a leakage-safe timestamp join after outcomes
    have resolved.
    """
    raw: dict[datetime, FeatureObservation] = {}
    for item in paths:
        path = Path(item)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            text = line.strip().lstrip("\ufeff")
            if not text.startswith("{"):
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            prediction = payload.get("prediction")
            if not isinstance(prediction, dict) or prediction.get("status") != "ok":
                continue
            surface = prediction.get("surface")
            timestamp_raw = prediction.get("timestamp")
            spot = _as_float(prediction.get("spot"))
            if not isinstance(surface, dict) or not timestamp_raw or spot is None:
                continue
            try:
                timestamp = datetime.fromisoformat(str(timestamp_raw))
                key = _utc_key(timestamp)
            except (TypeError, ValueError):
                continue
            raw[key] = FeatureObservation(
                timestamp=timestamp,
                spot=spot,
                local_gex=_as_float(surface.get("local_gex")),
                local_gex_slope=_as_float(surface.get("local_gex_slope")),
                hedge_acceleration=_as_float(surface.get("hedge_acceleration")),
                distance_to_flip=_as_float(surface.get("distance_to_flip")),
                distance_to_lower_wall=_as_float(surface.get("distance_to_lower_wall")),
                distance_to_upper_wall=_as_float(surface.get("distance_to_upper_wall")),
            )

    ordered = [raw[key] for key in sorted(raw)]
    enriched: list[FeatureObservation] = []
    previous: FeatureObservation | None = None
    for observation in ordered:
        same_session = (
            previous is not None
            and previous.timestamp.astimezone(_ET).date()
            == observation.timestamp.astimezone(_ET).date()
        )
        momentum = observation.spot - previous.spot if same_session and previous is not None else None
        enriched.append(
            FeatureObservation(
                timestamp=observation.timestamp,
                spot=observation.spot,
                local_gex=observation.local_gex,
                local_gex_slope=observation.local_gex_slope,
                hedge_acceleration=observation.hedge_acceleration,
                distance_to_flip=observation.distance_to_flip,
                distance_to_lower_wall=observation.distance_to_lower_wall,
                distance_to_upper_wall=observation.distance_to_upper_wall,
                spot_momentum_points=momentum,
            )
        )
        previous = observation
    return enriched


def join_shadow_rows(
    entries: Sequence[PredictionJournalEntry],
    observations: Sequence[FeatureObservation],
) -> list[JoinedShadowRow]:
    lookup = {_utc_key(observation.timestamp): observation for observation in observations}
    rows: list[JoinedShadowRow] = []
    for entry in entries:
        if not entry.resolved or entry.realized_move_points is None:
            continue
        observation = lookup.get(_utc_key(entry.created_at))
        if observation is not None:
            rows.append(JoinedShadowRow(entry=entry, observation=observation))
    return rows


def _realized_direction(row: JoinedShadowRow) -> str:
    move = float(row.entry.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = mean(xs)
    my = mean(ys)
    dx = [value - mx for value in xs]
    dy = [value - my for value in ys]
    denom = math.sqrt(sum(value * value for value in dx) * sum(value * value for value in dy))
    if denom == 0:
        return None
    return sum(left * right for left, right in zip(dx, dy)) / denom


def _score_rule(rows: Sequence[JoinedShadowRow], rule: Rule) -> dict[str, object]:
    scored: list[tuple[str, str]] = []
    for row in rows:
        predicted = rule(row)
        if predicted not in {"up", "down"}:
            continue
        scored.append((predicted, _realized_direction(row)))
    if not scored:
        return {
            "scored": 0,
            "directional_accuracy": None,
            "best_constant_direction_accuracy": None,
            "lift_vs_best_constant": None,
            "predicted_counts": {"up": 0, "down": 0},
            "realized_counts": {"up": 0, "down": 0, "flat": 0},
        }
    predicted_counts = {
        "up": sum(predicted == "up" for predicted, _ in scored),
        "down": sum(predicted == "down" for predicted, _ in scored),
    }
    realized_counts = {
        "up": sum(realized == "up" for _, realized in scored),
        "down": sum(realized == "down" for _, realized in scored),
        "flat": sum(realized == "flat" for _, realized in scored),
    }
    accuracy = sum(predicted == realized for predicted, realized in scored) / len(scored)
    best_constant = max(realized_counts["up"], realized_counts["down"]) / len(scored)
    return {
        "scored": len(scored),
        "directional_accuracy": accuracy,
        "best_constant_direction_accuracy": best_constant,
        "lift_vs_best_constant": accuracy - best_constant,
        "predicted_counts": predicted_counts,
        "realized_counts": realized_counts,
    }


def _signed_direction(value: float | None, *, inverted: bool = False) -> str | None:
    if value is None or value == 0:
        return None
    up = value > 0
    if inverted:
        up = not up
    return "up" if up else "down"


def _nearest_wall_direction(observation: FeatureObservation) -> str | None:
    lower = observation.distance_to_lower_wall
    upper = observation.distance_to_upper_wall
    if lower is None and upper is None:
        return None
    if lower is None:
        return "up"
    if upper is None:
        return "down"
    return "up" if upper < lower else "down"


def _candidate_rules() -> dict[str, Rule]:
    return {
        "current_prediction": lambda row: row.entry.prediction.direction,
        "always_down": lambda row: "down",
        "slope_direct": lambda row: _signed_direction(row.observation.local_gex_slope),
        "slope_inverted": lambda row: _signed_direction(row.observation.local_gex_slope, inverted=True),
        "hedge_acceleration_direct": lambda row: _signed_direction(row.observation.hedge_acceleration),
        "hedge_acceleration_inverted": lambda row: _signed_direction(row.observation.hedge_acceleration, inverted=True),
        "flip_away": lambda row: _signed_direction(row.observation.distance_to_flip),
        "flip_toward": lambda row: _signed_direction(row.observation.distance_to_flip, inverted=True),
        "nearest_wall": lambda row: _nearest_wall_direction(row.observation),
        "momentum_direct": lambda row: _signed_direction(row.observation.spot_momentum_points),
        "momentum_inverted": lambda row: _signed_direction(row.observation.spot_momentum_points, inverted=True),
    }


def _majority_direction(rows: Sequence[JoinedShadowRow]) -> str:
    up = sum(_realized_direction(row) == "up" for row in rows)
    down = sum(_realized_direction(row) == "down" for row in rows)
    return "up" if up > down else "down"


def _chronological_median_rule(
    rows: Sequence[JoinedShadowRow],
    getter: FeatureGetter,
    *,
    train_fraction: float = 0.70,
) -> dict[str, object]:
    timestamps = sorted({_utc_key(row.entry.created_at) for row in rows})
    if len(timestamps) < 4:
        return {"status": "insufficient_observations", "unique_observations": len(timestamps)}
    split_index = max(1, min(len(timestamps) - 1, int(len(timestamps) * train_fraction)))
    train_keys = set(timestamps[:split_index])
    train = [row for row in rows if _utc_key(row.entry.created_at) in train_keys and getter(row.observation) is not None]
    test = [row for row in rows if _utc_key(row.entry.created_at) not in train_keys and getter(row.observation) is not None]
    if not train or not test:
        return {"status": "insufficient_feature_coverage", "train_rows": len(train), "test_rows": len(test)}

    threshold = median(float(getter(row.observation)) for row in train if getter(row.observation) is not None)
    global_direction = _majority_direction(train)
    lower = [row for row in train if float(getter(row.observation)) <= threshold]  # type: ignore[arg-type]
    upper = [row for row in train if float(getter(row.observation)) > threshold]  # type: ignore[arg-type]
    lower_direction = _majority_direction(lower) if lower else global_direction
    upper_direction = _majority_direction(upper) if upper else global_direction

    def learned_rule(row: JoinedShadowRow) -> str | None:
        value = getter(row.observation)
        if value is None:
            return None
        return lower_direction if value <= threshold else upper_direction

    learned = _score_rule(test, learned_rule)
    baseline = _score_rule(test, lambda row: global_direction)
    return {
        "status": "ok",
        "train_fraction": train_fraction,
        "unique_observations": len(timestamps),
        "train_unique_observations": split_index,
        "test_unique_observations": len(timestamps) - split_index,
        "train_rows": len(train),
        "test_rows": len(test),
        "threshold": threshold,
        "lower_or_equal_direction": lower_direction,
        "upper_direction": upper_direction,
        "train_majority_direction": global_direction,
        "test_directional_accuracy": learned["directional_accuracy"],
        "test_baseline_accuracy": baseline["directional_accuracy"],
        "test_lift_vs_train_majority": (
            None
            if learned["directional_accuracy"] is None or baseline["directional_accuracy"] is None
            else float(learned["directional_accuracy"]) - float(baseline["directional_accuracy"])
        ),
    }


def _feature_summary(
    rows: Sequence[JoinedShadowRow],
    getter: FeatureGetter,
) -> dict[str, object]:
    available = [row for row in rows if getter(row.observation) is not None]
    values = [float(getter(row.observation)) for row in available]  # type: ignore[arg-type]
    realized = [float(row.entry.realized_move_points or 0.0) for row in available]

    by_prediction: dict[str, float | None] = {}
    by_realized: dict[str, float | None] = {}
    for direction in ("up", "down"):
        pred_values = [
            float(getter(row.observation))
            for row in available
            if row.entry.prediction.direction == direction
        ]
        realized_values = [
            float(getter(row.observation))
            for row in available
            if _realized_direction(row) == direction
        ]
        by_prediction[direction] = mean(pred_values) if pred_values else None
        by_realized[direction] = mean(realized_values) if realized_values else None

    return {
        "available_rows": len(available),
        "mean": mean(values) if values else None,
        "median": median(values) if values else None,
        "pearson_to_realized_move": _pearson(values, realized),
        "mean_by_current_prediction": by_prediction,
        "mean_by_realized_direction": by_realized,
        "chronological_median_rule": _chronological_median_rule(rows, getter),
    }


def build_shadow_feature_ablation(
    *,
    journal_path: str | Path = "data/gexy/shadow_predictions.jsonl",
    log_paths: Sequence[str | Path],
    horizons: Sequence[int] = (5, 15, 30, 60),
) -> dict[str, object]:
    entries = load_entries(journal_path)
    resolved = [entry for entry in entries if entry.resolved and entry.realized_move_points is not None]
    observations = load_feature_observations(log_paths)
    rows = join_shadow_rows(resolved, observations)

    rules = _candidate_rules()
    features: dict[str, FeatureGetter] = {
        "local_gex": lambda observation: observation.local_gex,
        "local_gex_slope": lambda observation: observation.local_gex_slope,
        "hedge_acceleration": lambda observation: observation.hedge_acceleration,
        "distance_to_flip": lambda observation: observation.distance_to_flip,
        "distance_to_lower_wall": lambda observation: observation.distance_to_lower_wall,
        "distance_to_upper_wall": lambda observation: observation.distance_to_upper_wall,
        "spot_momentum_points": lambda observation: observation.spot_momentum_points,
        "et_minute": lambda observation: observation.et_minute,
    }

    session_dates = sorted({observation.timestamp.astimezone(_ET).date().isoformat() for observation in observations})
    coverage = len(rows) / len(resolved) if resolved else 0.0
    by_horizon: dict[str, object] = {}
    for horizon in horizons:
        horizon_rows = [row for row in rows if row.entry.prediction.horizon_minutes == horizon]
        if horizon_rows:
            by_horizon[str(horizon)] = {
                name: _score_rule(horizon_rows, rule)
                for name, rule in rules.items()
            }

    return {
        "status": "ok" if rows else "insufficient_feature_history",
        "journal": str(journal_path),
        "log_paths": [str(path) for path in log_paths],
        "total_journal_entries": len(entries),
        "resolved_journal_entries": len(resolved),
        "feature_observations": len(observations),
        "matched_resolved_rows": len(rows),
        "matched_coverage": coverage,
        "session_dates": session_dates,
        "session_count": len(session_dates),
        "regime_counts": {
            regime: sum(row.entry.prediction.regime == regime for row in rows)
            for regime in sorted({row.entry.prediction.regime for row in rows})
        },
        "candidate_rules": {
            name: _score_rule(rows, rule)
            for name, rule in rules.items()
        },
        "features": {
            name: _feature_summary(rows, getter)
            for name, getter in features.items()
        },
        "by_horizon": by_horizon,
        "limitations": [
            "Surface features are reconstructed from collector logs and joined to resolved predictions by the exact live-predict timestamp.",
            "Multiple horizon rows can share one feature observation, so joined rows are correlated rather than independent samples.",
            (
                "Only one session date is available; chronological time holdout is reported, but session-level out-of-sample validation is not yet possible."
                if len(session_dates) < 2
                else "Multiple session dates are available; session-level validation should still be run before any model promotion."
            ),
            "All candidate rules and learned median splits are advisory research diagnostics; execution behavior is unchanged.",
        ],
    }
