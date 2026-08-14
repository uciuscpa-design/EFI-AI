from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from math import sqrt
from pathlib import Path
from statistics import mean
from typing import Iterable

from packages.gexy.prediction_journal import PredictionJournalEntry, load_entries

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTION_JOURNAL = ROOT / "data" / "gexy" / "live_predictions.jsonl"
DEFAULT_SHADOW_JOURNAL = ROOT / "data" / "gexy" / "shadow_predictions.jsonl"


@dataclass(frozen=True)
class BacktestMetrics:
    total_forecasts: int
    resolved: int
    resolution_coverage: float
    directional_accuracy: float
    always_down_accuracy: float
    always_up_accuracy: float
    best_constant_direction_accuracy: float
    lift_vs_best_constant: float
    mean_absolute_error_points: float
    root_mean_squared_error_points: float
    mean_bias_points: float
    mean_confidence: float
    calibration_gap: float


def _actual_direction(entry: PredictionJournalEntry) -> str:
    move = float(entry.realized_move_points or 0.0)
    return "up" if move > 0 else "down" if move < 0 else "flat"


def summarize(entries: Iterable[PredictionJournalEntry]) -> BacktestMetrics:
    rows = list(entries)
    resolved = [entry for entry in rows if entry.resolved]
    total = len(rows)
    n = len(resolved)
    coverage = n / total if total else 0.0
    if not resolved:
        return BacktestMetrics(
            total_forecasts=total,
            resolved=0,
            resolution_coverage=coverage,
            directional_accuracy=0.0,
            always_down_accuracy=0.0,
            always_up_accuracy=0.0,
            best_constant_direction_accuracy=0.0,
            lift_vs_best_constant=0.0,
            mean_absolute_error_points=0.0,
            root_mean_squared_error_points=0.0,
            mean_bias_points=0.0,
            mean_confidence=0.0,
            calibration_gap=0.0,
        )

    hits = sum(1 for entry in resolved if bool(entry.directional_hit))
    accuracy = hits / n
    down = sum(1 for entry in resolved if _actual_direction(entry) == "down") / n
    up = sum(1 for entry in resolved if _actual_direction(entry) == "up") / n
    baseline = max(down, up)
    errors = [float(entry.prediction.expected_move_points) - float(entry.realized_move_points or 0.0) for entry in resolved]
    confidence = mean(float(entry.prediction.confidence) for entry in resolved)
    return BacktestMetrics(
        total_forecasts=total,
        resolved=n,
        resolution_coverage=coverage,
        directional_accuracy=accuracy,
        always_down_accuracy=down,
        always_up_accuracy=up,
        best_constant_direction_accuracy=baseline,
        lift_vs_best_constant=accuracy - baseline,
        mean_absolute_error_points=mean(abs(error) for error in errors),
        root_mean_squared_error_points=sqrt(mean(error * error for error in errors)),
        mean_bias_points=mean(errors),
        mean_confidence=confidence,
        calibration_gap=confidence - accuracy,
    )


def _split_chronologically(entries: list[PredictionJournalEntry]) -> dict[str, list[PredictionJournalEntry]]:
    rows = sorted(entries, key=lambda entry: entry.created_at)
    n = len(rows)
    train_end = int(n * 0.60)
    validation_end = train_end + int(n * 0.20)
    return {
        "train": rows[:train_end],
        "validation": rows[train_end:validation_end],
        "test": rows[validation_end:],
    }


def build_report(
    entries: Iterable[PredictionJournalEntry],
    *,
    horizon_minutes: int | None = None,
    journal_label: str = "journal",
) -> dict[str, object]:
    rows = list(entries)
    if horizon_minutes is not None:
        if not 1 <= horizon_minutes <= 60:
            raise ValueError("horizon_minutes must be between 1 and 60")
        rows = [entry for entry in rows if entry.prediction.horizon_minutes == horizon_minutes]

    by_horizon: dict[str, object] = {}
    for horizon in sorted({entry.prediction.horizon_minutes for entry in rows}):
        horizon_rows = [entry for entry in rows if entry.prediction.horizon_minutes == horizon]
        by_horizon[str(horizon)] = asdict(summarize(horizon_rows))

    split_metrics = {
        name: asdict(summarize(split_rows))
        for name, split_rows in _split_chronologically(rows).items()
    }
    return {
        "journal": journal_label,
        "horizon_minutes": horizon_minutes,
        "research_only": True,
        "execution_enabled": False,
        "method": "frozen_prediction_journal_backtest",
        "note": "Metrics score predictions that were recorded before their realized outcomes. The best-constant baseline is diagnostic, not a fitted trading rule.",
        "overall": asdict(summarize(rows)),
        "chronological_splits": split_metrics,
        "by_horizon": by_horizon,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score frozen GEXY prediction journals without look-ahead")
    parser.add_argument("--source", choices=("production", "shadow"), default="shadow")
    parser.add_argument("--journal", help="optional explicit JSONL journal path")
    parser.add_argument("--horizon", type=int, help="optional 1-60 minute horizon filter")
    args = parser.parse_args()

    if args.journal:
        path = Path(args.journal).expanduser()
        if not path.is_absolute():
            path = ROOT / path
    else:
        path = DEFAULT_PRODUCTION_JOURNAL if args.source == "production" else DEFAULT_SHADOW_JOURNAL

    if not path.exists():
        print(json.dumps({"status": "error", "error": f"journal not found: {path}"}, indent=2))
        return 2

    try:
        report = build_report(load_entries(path), horizon_minutes=args.horizon, journal_label=str(path))
    except ValueError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2

    print(json.dumps({"status": "ok", **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
