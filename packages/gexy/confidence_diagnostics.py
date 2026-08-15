from __future__ import annotations

import math
from pathlib import Path
from statistics import mean, median
from typing import Sequence

from .prediction_journal import load_entries
from .shadow_feature_ablation import JoinedShadowRow, join_shadow_rows, load_feature_observations

UPPER_CONFIDENCE_CAP = 0.95
RAW_UPPER_CAP_THRESHOLD = -math.log(1.0 - UPPER_CONFIDENCE_CAP)


def _realized_direction(row: JoinedShadowRow) -> str:
    move = float(row.entry.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _percentile(values: Sequence[float], probability: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


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


def _components(row: JoinedShadowRow) -> dict[str, float]:
    observation = row.observation
    wall_candidates = [
        value
        for value in (
            observation.distance_to_lower_wall,
            observation.distance_to_upper_wall,
        )
        if value is not None
    ]
    wall_distance = min(wall_candidates) if wall_candidates else 25.0
    flip_distance = abs(observation.distance_to_flip) if observation.distance_to_flip is not None else 25.0
    slope_component = abs(float(observation.local_gex_slope or 0.0))
    hedge_component = abs(float(observation.hedge_acceleration or 0.0)) / 10.0
    structure = slope_component + hedge_component
    expected_move = abs(float(row.entry.prediction.expected_move_points))
    denominator = max(wall_distance + flip_distance + expected_move, 1.0)
    raw = structure / denominator
    unclipped = 1.0 - math.exp(-raw)
    recomputed = max(0.05, min(UPPER_CONFIDENCE_CAP, unclipped))
    return {
        "wall_distance": wall_distance,
        "flip_distance": flip_distance,
        "slope_component": slope_component,
        "hedge_component": hedge_component,
        "structure": structure,
        "expected_move_abs": expected_move,
        "denominator": denominator,
        "raw": raw,
        "unclipped_confidence": unclipped,
        "recomputed_confidence": recomputed,
        "slope_share_of_structure": slope_component / structure if structure else 0.0,
    }


def _direction_counts(rows: Sequence[JoinedShadowRow]) -> dict[str, int]:
    return {
        "up": sum(row.entry.prediction.direction == "up" for row in rows),
        "down": sum(row.entry.prediction.direction == "down" for row in rows),
        "flat": sum(row.entry.prediction.direction == "flat" for row in rows),
    }


def _realized_counts(rows: Sequence[JoinedShadowRow]) -> dict[str, int]:
    realized = [_realized_direction(row) for row in rows]
    return {
        "up": sum(value == "up" for value in realized),
        "down": sum(value == "down" for value in realized),
        "flat": sum(value == "flat" for value in realized),
    }


def _direction_summary(
    rows: Sequence[JoinedShadowRow],
    components: Sequence[dict[str, float]],
    *,
    direction: str,
) -> dict[str, object]:
    pairs = [
        (row, component)
        for row, component in zip(rows, components)
        if row.entry.prediction.direction == direction
    ]
    if not pairs:
        return {"rows": 0, "status": "no_rows"}

    selected_rows = [row for row, _ in pairs]
    raw = [component["raw"] for _, component in pairs]
    correctness = [
        1.0 if row.entry.prediction.direction == _realized_direction(row) else 0.0
        for row in selected_rows
    ]
    abs_realized_move = [abs(float(row.entry.realized_move_points or 0.0)) for row in selected_rows]
    return {
        "status": "ok",
        "rows": len(selected_rows),
        "directional_accuracy": mean(correctness),
        "realized_counts": _realized_counts(selected_rows),
        "raw_score": {
            "min": min(raw),
            "p25": _percentile(raw, 0.25),
            "median": median(raw),
            "p75": _percentile(raw, 0.75),
            "max": max(raw),
            "pearson_to_correctness": _pearson(raw, correctness),
            "pearson_to_abs_realized_move": _pearson(raw, abs_realized_move),
        },
    }


def _quartile_accuracy(rows: Sequence[JoinedShadowRow], raw_values: Sequence[float]) -> list[dict[str, object]]:
    if not rows:
        return []
    q1 = _percentile(raw_values, 0.25)
    q2 = _percentile(raw_values, 0.50)
    q3 = _percentile(raw_values, 0.75)
    assert q1 is not None and q2 is not None and q3 is not None
    boundaries = [(-math.inf, q1), (q1, q2), (q2, q3), (q3, math.inf)]
    output: list[dict[str, object]] = []
    for index, (lower, upper) in enumerate(boundaries, start=1):
        bucket: list[JoinedShadowRow] = []
        bucket_raw: list[float] = []
        for row, raw in zip(rows, raw_values):
            in_bucket = raw <= upper if index == 1 else lower < raw <= upper
            if index == 4:
                in_bucket = raw > lower
            if in_bucket:
                bucket.append(row)
                bucket_raw.append(raw)
        correct = sum(
            row.entry.prediction.direction == _realized_direction(row)
            for row in bucket
        )
        output.append(
            {
                "quartile": index,
                "rows": len(bucket),
                "raw_min": min(bucket_raw) if bucket_raw else None,
                "raw_max": max(bucket_raw) if bucket_raw else None,
                "directional_accuracy": correct / len(bucket) if bucket else None,
                "predicted_counts": _direction_counts(bucket),
                "realized_counts": _realized_counts(bucket),
                "predicted_down_fraction": (
                    sum(row.entry.prediction.direction == "down" for row in bucket) / len(bucket)
                    if bucket
                    else None
                ),
            }
        )
    return output


def _summarize(rows: Sequence[JoinedShadowRow]) -> dict[str, object]:
    if not rows:
        return {"rows": 0, "status": "no_rows"}

    components = [_components(row) for row in rows]
    reported = [float(row.entry.prediction.confidence) for row in rows]
    raw = [item["raw"] for item in components]
    slope = [item["slope_component"] for item in components]
    hedge = [item["hedge_component"] for item in components]
    denominator = [item["denominator"] for item in components]
    slope_share = [item["slope_share_of_structure"] for item in components]
    correctness = [
        1.0 if row.entry.prediction.direction == _realized_direction(row) else 0.0
        for row in rows
    ]
    abs_realized_move = [abs(float(row.entry.realized_move_points or 0.0)) for row in rows]

    cap_fraction = sum(value >= UPPER_CONFIDENCE_CAP - 1e-12 for value in reported) / len(reported)
    raw_cap_fraction = sum(value >= RAW_UPPER_CAP_THRESHOLD for value in raw) / len(raw)
    return {
        "status": "ok",
        "rows": len(rows),
        "unique_observations": len({row.entry.created_at for row in rows}),
        "directional_accuracy": mean(correctness),
        "predicted_counts": _direction_counts(rows),
        "realized_counts": _realized_counts(rows),
        "reported_confidence": {
            "min": min(reported),
            "median": median(reported),
            "max": max(reported),
            "unique_rounded_6dp": sorted({round(value, 6) for value in reported}),
            "upper_cap_fraction": cap_fraction,
        },
        "raw_score": {
            "upper_cap_threshold": RAW_UPPER_CAP_THRESHOLD,
            "min": min(raw),
            "p25": _percentile(raw, 0.25),
            "median": median(raw),
            "p75": _percentile(raw, 0.75),
            "p95": _percentile(raw, 0.95),
            "max": max(raw),
            "fraction_at_or_above_upper_cap_threshold": raw_cap_fraction,
            "pearson_to_correctness": _pearson(raw, correctness),
            "pearson_to_abs_realized_move": _pearson(raw, abs_realized_move),
        },
        "components": {
            "median_abs_local_gex_slope": median(slope),
            "median_abs_hedge_acceleration_div10": median(hedge),
            "median_denominator": median(denominator),
            "median_slope_share_of_structure": median(slope_share),
            "p05_slope_share_of_structure": _percentile(slope_share, 0.05),
        },
        "by_predicted_direction": {
            direction: _direction_summary(rows, components, direction=direction)
            for direction in ("up", "down")
        },
        "accuracy_by_raw_quartile": _quartile_accuracy(rows, raw),
        "saturation_confirmed": cap_fraction >= 0.95 and raw_cap_fraction >= 0.95,
    }


def build_confidence_diagnostics(
    *,
    journal_path: str | Path = "data/gexy/shadow_predictions.jsonl",
    log_paths: Sequence[str | Path],
    horizons: Sequence[int] = (5, 15, 30, 60),
) -> dict[str, object]:
    entries = load_entries(journal_path)
    observations = load_feature_observations(log_paths)
    rows = join_shadow_rows(entries, observations)

    by_horizon: dict[str, object] = {}
    for horizon in horizons:
        horizon_rows = [row for row in rows if row.entry.prediction.horizon_minutes == horizon]
        if horizon_rows:
            by_horizon[str(horizon)] = _summarize(horizon_rows)

    overall = _summarize(rows)
    return {
        "status": "ok" if rows else "insufficient_feature_history",
        "journal": str(journal_path),
        "log_paths": [str(path) for path in log_paths],
        "feature_observations": len(observations),
        "matched_resolved_rows": len(rows),
        "formula_audited": "raw=(abs(local_gex_slope)+abs(hedge_acceleration)/10)/max(min_wall_distance+abs(flip_distance)+abs(expected_move),1); confidence=clamp(1-exp(-raw),0.05,0.95)",
        "upper_confidence_cap": UPPER_CONFIDENCE_CAP,
        "raw_upper_cap_threshold": RAW_UPPER_CAP_THRESHOLD,
        "overall": overall,
        "by_horizon": by_horizon,
        "interpretation": [
            "Reported confidence is not a calibrated probability and must not be treated as one.",
            "If local-GEX slope dominates the structure term, the current formula mixes incompatible feature scales and can saturate mechanically.",
            "Raw-score accuracy must be inspected within predicted direction because direction imbalance can create false confidence ranking.",
            "Rescaling alone is not sufficient evidence of predictive confidence; any replacement must be calibrated on earlier data and validated on later independent sessions.",
            "This diagnostic does not modify the production predictor and does not authorize execution.",
        ],
        "production_predictor_changed": False,
        "execution_authorized": False,
    }
