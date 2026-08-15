from __future__ import annotations

from datetime import timezone
from pathlib import Path
from typing import Callable, Sequence

from .prediction_journal import PredictionJournalEntry, load_entries
from .shadow_feature_ablation import JoinedShadowRow, join_shadow_rows, load_feature_observations

Rule = Callable[[JoinedShadowRow], str | None]


def _realized_direction(row: JoinedShadowRow) -> str:
    move = float(row.entry.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def _score(rows: Sequence[JoinedShadowRow], rule: Rule) -> dict[str, object]:
    scored: list[tuple[str, str]] = []
    for row in rows:
        predicted = rule(row)
        if predicted not in {"up", "down"}:
            continue
        scored.append((predicted, _realized_direction(row)))
    if not scored:
        return {"scored": 0, "directional_accuracy": None}
    return {
        "scored": len(scored),
        "directional_accuracy": sum(predicted == realized for predicted, realized in scored) / len(scored),
        "realized_down": sum(realized == "down" for _, realized in scored),
        "realized_up": sum(realized == "up" for _, realized in scored),
        "realized_flat": sum(realized == "flat" for _, realized in scored),
    }


def _slope_inverted(row: JoinedShadowRow) -> str | None:
    slope = row.observation.local_gex_slope
    if slope is None or slope == 0:
        return None
    return "down" if slope > 0 else "up"


def _utc_timestamp(row: JoinedShadowRow):
    return row.entry.created_at.astimezone(timezone.utc)


def _split_rows(
    rows: Sequence[JoinedShadowRow],
    *,
    train_fraction: float,
) -> tuple[list[JoinedShadowRow], list[JoinedShadowRow], int, int]:
    timestamps = sorted({_utc_timestamp(row) for row in rows})
    if len(timestamps) < 4:
        return [], [], 0, 0
    split_index = max(1, min(len(timestamps) - 1, int(len(timestamps) * train_fraction)))
    train_keys = set(timestamps[:split_index])
    train = [row for row in rows if _utc_timestamp(row) in train_keys]
    test = [row for row in rows if _utc_timestamp(row) not in train_keys]
    return train, test, split_index, len(timestamps) - split_index


def _lift(metric: dict[str, object], baseline: dict[str, object]) -> float | None:
    value = metric.get("directional_accuracy")
    base = baseline.get("directional_accuracy")
    if value is None or base is None:
        return None
    return float(value) - float(base)


def build_horizon_holdout(
    *,
    journal_path: str | Path = "data/gexy/shadow_predictions.jsonl",
    log_paths: Sequence[str | Path],
    horizons: Sequence[int] = (5, 15, 30, 60),
    train_fraction: float = 0.70,
) -> dict[str, object]:
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")

    entries: list[PredictionJournalEntry] = load_entries(journal_path)
    observations = load_feature_observations(log_paths)
    rows = join_shadow_rows(entries, observations)

    rules: dict[str, Rule] = {
        "always_down": lambda row: "down",
        "current_prediction": lambda row: row.entry.prediction.direction,
        "slope_inverted": _slope_inverted,
    }

    by_horizon: dict[str, object] = {}
    for horizon in horizons:
        horizon_rows = [row for row in rows if row.entry.prediction.horizon_minutes == horizon]
        train, test, train_observations, test_observations = _split_rows(
            horizon_rows,
            train_fraction=train_fraction,
        )
        if not train or not test:
            continue
        train_metrics = {name: _score(train, rule) for name, rule in rules.items()}
        test_metrics = {name: _score(test, rule) for name, rule in rules.items()}
        baseline_test = test_metrics["always_down"]
        by_horizon[str(horizon)] = {
            "train_fraction": train_fraction,
            "train_unique_observations": train_observations,
            "test_unique_observations": test_observations,
            "train": train_metrics,
            "test": test_metrics,
            "test_lift_vs_always_down": {
                "current_prediction": _lift(test_metrics["current_prediction"], baseline_test),
                "slope_inverted": _lift(test_metrics["slope_inverted"], baseline_test),
            },
            "slope_inversion_supported_on_late_holdout": (
                test_metrics["slope_inverted"].get("scored", 0) >= 30
                and (_lift(test_metrics["slope_inverted"], baseline_test) or 0.0) > 0.0
            ),
        }

    return {
        "status": "ok" if by_horizon else "insufficient_feature_history",
        "journal": str(journal_path),
        "matched_rows": len(rows),
        "feature_observations": len(observations),
        "train_fraction": train_fraction,
        "by_horizon": by_horizon,
        "interpretation_guardrails": [
            "The late-window test is chronological within a single session, not a separate-session out-of-sample test.",
            "The 5-minute slope-inversion hypothesis was identified after inspecting the same session, so any positive late-window result is still exploratory.",
            "No result from this report changes the production predictor or enables execution.",
        ],
    }
