from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from packages.gexy.prediction_journal import PredictionJournalEntry, load_entries

_ET = ZoneInfo("America/New_York")


def _resolved(entries: list[PredictionJournalEntry]) -> list[PredictionJournalEntry]:
    return [entry for entry in entries if entry.resolved and entry.realized_move_points is not None]


def _accuracy(rows: list[PredictionJournalEntry]) -> float | None:
    if not rows:
        return None
    return sum(bool(row.directional_hit) for row in rows) / len(rows)


def _realized_direction(row: PredictionJournalEntry) -> str:
    move = float(row.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _inverted_hit(row: PredictionJournalEntry) -> bool | None:
    realized = _realized_direction(row)
    if row.prediction.direction == "up":
        return realized == "down"
    if row.prediction.direction == "down":
        return realized == "up"
    return None


def _inverted_accuracy(rows: list[PredictionJournalEntry]) -> float | None:
    values = [value for row in rows if (value := _inverted_hit(row)) is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _keep_down_flip_up_accuracy(rows: list[PredictionJournalEntry]) -> tuple[int, float | None]:
    values: list[bool] = []
    for row in rows:
        if row.prediction.direction == "down":
            values.append(bool(row.directional_hit))
        elif row.prediction.direction == "up":
            inverted = _inverted_hit(row)
            if inverted is not None:
                values.append(inverted)
    if not values:
        return 0, None
    return len(values), sum(values) / len(values)


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = mean(xs)
    my = mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    denom = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    if denom == 0:
        return None
    return sum(a * b for a, b in zip(dx, dy)) / denom


def _group_summary(rows: list[PredictionJournalEntry]) -> dict[str, object]:
    if not rows:
        return {
            "resolved": 0,
            "directional_accuracy": None,
            "inverted_directional_accuracy": None,
            "mean_absolute_error_points": None,
            "mean_confidence": None,
            "realized_direction_counts": {"up": 0, "down": 0, "flat": 0},
            "always_up_accuracy": None,
            "always_down_accuracy": None,
            "best_constant_direction_accuracy": None,
            "model_lift_vs_best_constant": None,
        }

    counts = {"up": 0, "down": 0, "flat": 0}
    for row in rows:
        counts[_realized_direction(row)] += 1

    directional_accuracy = _accuracy(rows)
    always_up = counts["up"] / len(rows)
    always_down = counts["down"] / len(rows)
    best_constant = max(always_up, always_down)
    return {
        "resolved": len(rows),
        "directional_accuracy": directional_accuracy,
        "inverted_directional_accuracy": _inverted_accuracy(rows),
        "mean_absolute_error_points": mean(float(row.absolute_error_points or 0.0) for row in rows),
        "mean_confidence": mean(row.prediction.confidence for row in rows),
        "realized_direction_counts": counts,
        "always_up_accuracy": always_up,
        "always_down_accuracy": always_down,
        "best_constant_direction_accuracy": best_constant,
        "model_lift_vs_best_constant": (
            directional_accuracy - best_constant if directional_accuracy is not None else None
        ),
    }


def build_diagnostics(path: str | Path) -> dict[str, object]:
    entries = load_entries(path)
    rows = _resolved(entries)

    by_horizon: dict[int, list[PredictionJournalEntry]] = defaultdict(list)
    by_regime: dict[str, list[PredictionJournalEntry]] = defaultdict(list)
    by_direction: dict[str, list[PredictionJournalEntry]] = defaultdict(list)
    by_et_hour: dict[int, list[PredictionJournalEntry]] = defaultdict(list)
    by_horizon_direction: dict[int, dict[str, list[PredictionJournalEntry]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for row in rows:
        horizon = row.prediction.horizon_minutes
        direction = row.prediction.direction
        by_horizon[horizon].append(row)
        by_regime[row.prediction.regime].append(row)
        by_direction[direction].append(row)
        by_et_hour[row.created_at.astimezone(_ET).hour].append(row)
        by_horizon_direction[horizon][direction].append(row)

    horizon_metrics = {str(k): _group_summary(v) for k, v in sorted(by_horizon.items())}
    eligible = [
        (horizon, metrics)
        for horizon, metrics in horizon_metrics.items()
        if int(metrics["resolved"]) >= 30
    ]
    best_raw = max(eligible, key=lambda item: item[1]["directional_accuracy"] or -1.0) if eligible else None
    best_inverted = max(
        eligible,
        key=lambda item: item[1]["inverted_directional_accuracy"] or -1.0,
    ) if eligible else None

    horizon_direction_metrics: dict[str, dict[str, dict[str, object]]] = {}
    direction_candidates: list[tuple[int, str, dict[str, object]]] = []
    for horizon, directions in sorted(by_horizon_direction.items()):
        horizon_direction_metrics[str(horizon)] = {}
        for direction, group_rows in sorted(directions.items()):
            summary = _group_summary(group_rows)
            horizon_direction_metrics[str(horizon)][direction] = summary
            if int(summary["resolved"]) >= 30:
                direction_candidates.append((horizon, direction, summary))

    best_horizon_direction = (
        max(direction_candidates, key=lambda item: item[2]["directional_accuracy"] or -1.0)
        if direction_candidates
        else None
    )

    predicted_moves = [row.prediction.expected_move_points for row in rows]
    realized_moves = [float(row.realized_move_points or 0.0) for row in rows]
    confidences = [row.prediction.confidence for row in rows]
    counterfactual_scored, counterfactual_accuracy = _keep_down_flip_up_accuracy(rows)

    correlation_by_direction: dict[str, float | None] = {}
    for direction, group_rows in sorted(by_direction.items()):
        correlation_by_direction[direction] = _pearson(
            [row.prediction.expected_move_points for row in group_rows],
            [float(row.realized_move_points or 0.0) for row in group_rows],
        )

    return {
        "journal": str(path),
        "total_entries": len(entries),
        "resolved_entries": len(rows),
        "overall": _group_summary(rows),
        "expected_vs_realized_move_correlation": _pearson(predicted_moves, realized_moves),
        "expected_vs_realized_move_correlation_by_direction": correlation_by_direction,
        "confidence": {
            "min": min(confidences) if confidences else None,
            "max": max(confidences) if confidences else None,
            "mean": mean(confidences) if confidences else None,
            "unique_rounded_4dp": sorted({round(value, 4) for value in confidences}),
        },
        "counterfactual_keep_down_flip_up": {
            "scored": counterfactual_scored,
            "directional_accuracy": counterfactual_accuracy,
            "advisory_only": True,
        },
        "best_raw_horizon_min_30": (
            {"horizon_minutes": int(best_raw[0]), **best_raw[1]} if best_raw else None
        ),
        "best_inverted_horizon_min_30": (
            {"horizon_minutes": int(best_inverted[0]), **best_inverted[1]} if best_inverted else None
        ),
        "best_horizon_direction_min_30": (
            {
                "horizon_minutes": best_horizon_direction[0],
                "predicted_direction": best_horizon_direction[1],
                **best_horizon_direction[2],
            }
            if best_horizon_direction
            else None
        ),
        "by_horizon": horizon_metrics,
        "by_horizon_direction": horizon_direction_metrics,
        "by_regime": {key: _group_summary(value) for key, value in sorted(by_regime.items())},
        "by_direction": {key: _group_summary(value) for key, value in sorted(by_direction.items())},
        "by_et_hour": {str(key): _group_summary(value) for key, value in sorted(by_et_hour.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose GEXY fine-shadow forecast behavior")
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    args = parser.parse_args()
    print(json.dumps(build_diagnostics(args.journal), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
