from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

from .live_prediction import PRODUCTION_HORIZONS_MINUTES
from .prediction_journal import PredictionJournalEntry, load_entries

_ET = ZoneInfo("America/New_York")

MODEL_ID = "GEXY-CONFIDENCE-CAL-v1"
SELECTION_SESSION = date(2026, 8, 14)
SUPPORTED_REGIME = "negative_gamma_acceleration"
SUPPORTED_DIRECTIONS = ("up", "down")
JEFFREYS_ALPHA = 0.5
JEFFREYS_BETA = 0.5
MIN_CELL_ROWS = 20
MIN_INDEPENDENT_SESSION_ROWS = 50
REQUIRED_POSITIVE_INDEPENDENT_SESSIONS = 2


def _session_date(entry: PredictionJournalEntry) -> date:
    return entry.created_at.astimezone(_ET).date()


def _eligible(entry: PredictionJournalEntry) -> bool:
    return (
        entry.resolved
        and entry.directional_hit is not None
        and entry.prediction.horizon_minutes in PRODUCTION_HORIZONS_MINUTES
        and entry.prediction.regime == SUPPORTED_REGIME
        and entry.prediction.direction in SUPPORTED_DIRECTIONS
    )


def _posterior_mean(hits: int, rows: int) -> float:
    return (hits + JEFFREYS_ALPHA) / (rows + JEFFREYS_ALPHA + JEFFREYS_BETA)


def _model_fingerprint(model: dict[str, object]) -> str:
    payload = json.dumps(model, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fit_selection_model(entries: Iterable[PredictionJournalEntry]) -> dict[str, object]:
    selection = [
        entry
        for entry in entries
        if _eligible(entry) and _session_date(entry) == SELECTION_SESSION
    ]

    cells: dict[str, dict[str, object]] = {}
    horizon_baselines: dict[str, dict[str, object]] = {}
    for horizon in PRODUCTION_HORIZONS_MINUTES:
        horizon_rows = [entry for entry in selection if entry.prediction.horizon_minutes == horizon]
        horizon_hits = sum(bool(entry.directional_hit) for entry in horizon_rows)
        horizon_baselines[str(horizon)] = {
            "rows": len(horizon_rows),
            "hits": horizon_hits,
            "observed_accuracy": horizon_hits / len(horizon_rows) if horizon_rows else None,
            "posterior_probability_correct": (
                _posterior_mean(horizon_hits, len(horizon_rows)) if horizon_rows else None
            ),
        }
        for direction in SUPPORTED_DIRECTIONS:
            group = [entry for entry in horizon_rows if entry.prediction.direction == direction]
            hits = sum(bool(entry.directional_hit) for entry in group)
            cells[f"{horizon}:{direction}"] = {
                "horizon_minutes": horizon,
                "direction": direction,
                "rows": len(group),
                "hits": hits,
                "observed_accuracy": hits / len(group) if group else None,
                "posterior_probability_correct": (
                    _posterior_mean(hits, len(group)) if len(group) >= MIN_CELL_ROWS else None
                ),
                "minimum_rows_met": len(group) >= MIN_CELL_ROWS,
            }

    model_core: dict[str, object] = {
        "model_id": MODEL_ID,
        "selection_session": SELECTION_SESSION.isoformat(),
        "supported_regime": SUPPORTED_REGIME,
        "supported_horizons_minutes": list(PRODUCTION_HORIZONS_MINUTES),
        "supported_directions": list(SUPPORTED_DIRECTIONS),
        "smoothing": {
            "method": "Jeffreys Beta posterior mean",
            "alpha": JEFFREYS_ALPHA,
            "beta": JEFFREYS_BETA,
        },
        "minimum_cell_rows": MIN_CELL_ROWS,
        "selection_rows": len(selection),
        "cells": cells,
        "horizon_only_baselines": horizon_baselines,
    }
    return {**model_core, "fingerprint_sha256": _model_fingerprint(model_core)}


def _probability_for_entry(entry: PredictionJournalEntry, model: dict[str, object]) -> float | None:
    if not _eligible(entry):
        return None
    cells = model.get("cells")
    if not isinstance(cells, dict):
        return None
    cell = cells.get(f"{entry.prediction.horizon_minutes}:{entry.prediction.direction}")
    if not isinstance(cell, dict):
        return None
    value = cell.get("posterior_probability_correct")
    return None if value is None else float(value)


def _horizon_baseline_for_entry(entry: PredictionJournalEntry, model: dict[str, object]) -> float | None:
    baselines = model.get("horizon_only_baselines")
    if not isinstance(baselines, dict):
        return None
    cell = baselines.get(str(entry.prediction.horizon_minutes))
    if not isinstance(cell, dict):
        return None
    value = cell.get("posterior_probability_correct")
    return None if value is None else float(value)


def _brier(probabilities: Sequence[float], outcomes: Sequence[float]) -> float | None:
    if not probabilities or len(probabilities) != len(outcomes):
        return None
    return mean((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes))


def _log_loss(probabilities: Sequence[float], outcomes: Sequence[float]) -> float | None:
    if not probabilities or len(probabilities) != len(outcomes):
        return None
    epsilon = 1e-12
    return mean(
        -(outcome * math.log(min(max(probability, epsilon), 1.0 - epsilon))
          + (1.0 - outcome) * math.log(min(max(1.0 - probability, epsilon), 1.0 - epsilon)))
        for probability, outcome in zip(probabilities, outcomes)
    )


def _evaluate(entries: Sequence[PredictionJournalEntry], model: dict[str, object]) -> dict[str, object]:
    scored: list[tuple[PredictionJournalEntry, float, float, float]] = []
    for entry in entries:
        probability = _probability_for_entry(entry, model)
        horizon_baseline = _horizon_baseline_for_entry(entry, model)
        if probability is None or horizon_baseline is None:
            continue
        outcome = 1.0 if bool(entry.directional_hit) else 0.0
        scored.append((entry, probability, horizon_baseline, outcome))

    if not scored:
        return {
            "scored": 0,
            "status": "no_scored_rows",
            "mean_probability_correct": None,
            "observed_accuracy": None,
            "calibration_gap": None,
            "brier": None,
            "horizon_only_brier": None,
            "constant_0_5_brier": None,
            "brier_improvement_vs_horizon_only": None,
            "brier_improvement_vs_0_5": None,
            "log_loss": None,
        }

    probabilities = [probability for _, probability, _, _ in scored]
    horizon_probabilities = [baseline for _, _, baseline, _ in scored]
    outcomes = [outcome for _, _, _, outcome in scored]
    candidate_brier = _brier(probabilities, outcomes)
    horizon_brier = _brier(horizon_probabilities, outcomes)
    half_brier = _brier([0.5] * len(outcomes), outcomes)
    assert candidate_brier is not None and horizon_brier is not None and half_brier is not None

    by_cell: dict[str, dict[str, object]] = {}
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for entry, probability, _, outcome in scored:
        grouped[f"{entry.prediction.horizon_minutes}:{entry.prediction.direction}"].append((probability, outcome))
    for key, values in sorted(grouped.items()):
        cell_probabilities = [probability for probability, _ in values]
        cell_outcomes = [outcome for _, outcome in values]
        by_cell[key] = {
            "rows": len(values),
            "mean_probability_correct": mean(cell_probabilities),
            "observed_accuracy": mean(cell_outcomes),
            "calibration_gap": mean(cell_probabilities) - mean(cell_outcomes),
            "brier": _brier(cell_probabilities, cell_outcomes),
        }

    return {
        "status": "ok",
        "scored": len(scored),
        "mean_probability_correct": mean(probabilities),
        "observed_accuracy": mean(outcomes),
        "calibration_gap": mean(probabilities) - mean(outcomes),
        "brier": candidate_brier,
        "horizon_only_brier": horizon_brier,
        "constant_0_5_brier": half_brier,
        "brier_improvement_vs_horizon_only": horizon_brier - candidate_brier,
        "brier_improvement_vs_0_5": half_brier - candidate_brier,
        "log_loss": _log_loss(probabilities, outcomes),
        "by_cell": by_cell,
    }


def build_confidence_calibration_v1_report(
    *,
    journal_path: str | Path = "data/gexy/shadow_predictions.jsonl",
) -> dict[str, object]:
    entries = load_entries(journal_path)
    model = fit_selection_model(entries)
    selection_entries = [
        entry
        for entry in entries
        if _eligible(entry) and _session_date(entry) == SELECTION_SESSION
    ]
    selection_fit = _evaluate(selection_entries, model)

    future_dates = sorted({
        _session_date(entry)
        for entry in entries
        if _eligible(entry) and _session_date(entry) > SELECTION_SESSION
    })
    independent_sessions: list[dict[str, object]] = []
    for session_date in future_dates:
        session_entries = [
            entry
            for entry in entries
            if _eligible(entry) and _session_date(entry) == session_date
        ]
        evaluation = _evaluate(session_entries, model)
        informative = int(evaluation["scored"]) >= MIN_INDEPENDENT_SESSION_ROWS
        positive = bool(
            informative
            and evaluation["brier_improvement_vs_horizon_only"] is not None
            and float(evaluation["brier_improvement_vs_horizon_only"]) > 0.0
            and evaluation["brier_improvement_vs_0_5"] is not None
            and float(evaluation["brier_improvement_vs_0_5"]) > 0.0
        )
        independent_sessions.append({
            "session_date": session_date.isoformat(),
            "informative": informative,
            "minimum_rows": MIN_INDEPENDENT_SESSION_ROWS,
            "positive_calibration_result": positive,
            **evaluation,
        })

    informative_sessions = [item for item in independent_sessions if item["informative"]]
    positive_sessions = [item for item in informative_sessions if item["positive_calibration_result"]]
    informative_dates = {date.fromisoformat(str(item["session_date"])) for item in informative_sessions}
    aggregate_entries = [
        entry
        for entry in entries
        if _eligible(entry) and _session_date(entry) in informative_dates
    ]
    aggregate = _evaluate(aggregate_entries, model)
    aggregate_positive = bool(
        aggregate["brier_improvement_vs_horizon_only"] is not None
        and float(aggregate["brier_improvement_vs_horizon_only"]) > 0.0
        and aggregate["brier_improvement_vs_0_5"] is not None
        and float(aggregate["brier_improvement_vs_0_5"]) > 0.0
    )
    gate_met = (
        len(positive_sessions) >= REQUIRED_POSITIVE_INDEPENDENT_SESSIONS
        and aggregate_positive
    )

    if gate_met:
        status = "eligible_for_shadow_reliability_review"
    elif not independent_sessions:
        status = "awaiting_independent_sessions"
    elif not informative_sessions:
        status = "awaiting_informative_sessions"
    else:
        status = "collecting_independent_evidence"

    return {
        "status": status,
        "model": model,
        "selection_fit_diagnostic": selection_fit,
        "independent_sessions": independent_sessions,
        "promotion_gate": {
            "minimum_rows_per_informative_session": MIN_INDEPENDENT_SESSION_ROWS,
            "required_positive_independent_sessions": REQUIRED_POSITIVE_INDEPENDENT_SESSIONS,
            "positive_result_definition": "candidate Brier must beat both the frozen horizon-only selection baseline and constant 0.5 on the same future rows",
            "informative_session_count": len(informative_sessions),
            "positive_session_count": len(positive_sessions),
            "aggregate": aggregate,
            "aggregate_positive": aggregate_positive,
            "met": gate_met,
        },
        "meaning": "posterior_probability_correct estimates P(the current predicted direction is correct); it does not alter the predicted direction",
        "selection_session_is_validation": False,
        "production_confidence_replacement_authorized": False,
        "production_direction_change_authorized": False,
        "execution_authorized": False,
        "guardrails": [
            "The model is fit only on the 2026-08-14 selection session and negative-gamma production-horizon forecasts.",
            "Unsupported regimes, horizons, directions, or undersized selection cells are unscored rather than assigned fabricated reliability.",
            "Probabilities below 0.5 are allowed because the quantity is forecast correctness probability, not a forced certainty score.",
            "Future evaluation uses Brier score on separately captured sessions; the selection fit is diagnostic only.",
            "Passing this gate would authorize only review of a separate shadow reliability layer, not production or execution.",
        ],
    }
