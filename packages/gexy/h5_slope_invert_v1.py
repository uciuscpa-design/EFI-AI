from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Callable, Sequence
from zoneinfo import ZoneInfo

from .prediction_journal import PredictionJournalEntry, load_entries
from .shadow_feature_ablation import JoinedShadowRow, join_shadow_rows, load_feature_observations

_ET = ZoneInfo("America/New_York")

HYPOTHESIS_ID = "GEXY-H5-SLOPE-INVERT-v1"
SELECTION_SESSION = date(2026, 8, 14)
HORIZON_MINUTES = 5
REGIME = "negative_gamma_acceleration"
MIN_MATCHED_5M_ROWS = 50
REQUIRED_POSITIVE_INDEPENDENT_SESSIONS = 2

Rule = Callable[[JoinedShadowRow], str | None]


def _session_date_from_entry(entry: PredictionJournalEntry) -> date:
    return entry.created_at.astimezone(_ET).date()


def _session_date(row: JoinedShadowRow) -> date:
    return row.entry.created_at.astimezone(_ET).date()


def _realized_direction(row: JoinedShadowRow) -> str:
    move = float(row.entry.realized_move_points or 0.0)
    if move > 0:
        return "up"
    if move < 0:
        return "down"
    return "flat"


def frozen_rule(row: JoinedShadowRow) -> str | None:
    """Frozen v1 rule. Do not add thresholds or extra features to this version."""
    slope = row.observation.local_gex_slope
    if slope is None or slope == 0:
        return None
    return "down" if slope > 0 else "up"


def _score(rows: Sequence[JoinedShadowRow], rule: Rule) -> dict[str, object]:
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
            "predicted_counts": {"up": 0, "down": 0},
            "realized_counts": {"up": 0, "down": 0, "flat": 0},
        }

    return {
        "scored": len(scored),
        "directional_accuracy": sum(predicted == realized for predicted, realized in scored) / len(scored),
        "predicted_counts": {
            "up": sum(predicted == "up" for predicted, _ in scored),
            "down": sum(predicted == "down" for predicted, _ in scored),
        },
        "realized_counts": {
            "up": sum(realized == "up" for _, realized in scored),
            "down": sum(realized == "down" for _, realized in scored),
            "flat": sum(realized == "flat" for _, realized in scored),
        },
    }


def _lift(metric: dict[str, object], baseline: dict[str, object]) -> float | None:
    value = metric.get("directional_accuracy")
    base = baseline.get("directional_accuracy")
    if value is None or base is None:
        return None
    return float(value) - float(base)


def _eligible_rows(rows: Sequence[JoinedShadowRow]) -> list[JoinedShadowRow]:
    return [
        row
        for row in rows
        if row.entry.prediction.horizon_minutes == HORIZON_MINUTES
        and row.entry.prediction.regime == REGIME
        and row.observation.local_gex_slope not in {None, 0}
    ]


def _session_report(
    *,
    session_date: date,
    rows: Sequence[JoinedShadowRow],
    resolved_5m_journal_rows: int,
) -> dict[str, object]:
    matched_5m = [row for row in rows if row.entry.prediction.horizon_minutes == HORIZON_MINUTES]
    negative_gamma = [row for row in matched_5m if row.entry.prediction.regime == REGIME]
    eligible = _eligible_rows(rows)

    frozen = _score(eligible, frozen_rule)
    always_down = _score(eligible, lambda row: "down")
    current = _score(eligible, lambda row: row.entry.prediction.direction)
    lift = _lift(frozen, always_down)
    informative = len(matched_5m) >= MIN_MATCHED_5M_ROWS

    return {
        "session_date": session_date.isoformat(),
        "selection_session": session_date == SELECTION_SESSION,
        "resolved_5m_journal_rows": resolved_5m_journal_rows,
        "matched_5m_rows": len(matched_5m),
        "matched_5m_coverage": (
            len(matched_5m) / resolved_5m_journal_rows if resolved_5m_journal_rows else 0.0
        ),
        "negative_gamma_rows": len(negative_gamma),
        "slope_scorable_rows": len(eligible),
        "slope_coverage_of_negative_gamma": (
            len(eligible) / len(negative_gamma) if negative_gamma else 0.0
        ),
        "informative": informative,
        "minimum_matched_5m_rows": MIN_MATCHED_5M_ROWS,
        "frozen_rule": frozen,
        "always_down": always_down,
        "current_prediction": current,
        "lift_vs_always_down": lift,
        "positive_lift": bool(informative and lift is not None and lift > 0.0),
    }


def build_h5_slope_invert_v1_report(
    *,
    journal_path: str | Path = "data/gexy/shadow_predictions.jsonl",
    log_paths: Sequence[str | Path],
) -> dict[str, object]:
    entries = load_entries(journal_path)
    observations = load_feature_observations(log_paths)
    rows = join_shadow_rows(entries, observations)

    resolved_5m = [
        entry
        for entry in entries
        if entry.resolved
        and entry.realized_move_points is not None
        and entry.prediction.horizon_minutes == HORIZON_MINUTES
    ]
    resolved_by_date = Counter(_session_date_from_entry(entry) for entry in resolved_5m)
    rows_by_date: dict[date, list[JoinedShadowRow]] = {}
    for row in rows:
        rows_by_date.setdefault(_session_date(row), []).append(row)

    observed_dates = sorted(set(resolved_by_date) | set(rows_by_date))
    selection_dates = [value for value in observed_dates if value <= SELECTION_SESSION]
    independent_dates = [value for value in observed_dates if value > SELECTION_SESSION]

    independent_reports = [
        _session_report(
            session_date=value,
            rows=rows_by_date.get(value, []),
            resolved_5m_journal_rows=resolved_by_date.get(value, 0),
        )
        for value in independent_dates
    ]
    informative_reports = [report for report in independent_reports if report["informative"]]
    positive_reports = [report for report in informative_reports if report["positive_lift"]]

    informative_dates = {date.fromisoformat(str(report["session_date"])) for report in informative_reports}
    aggregate_rows = [
        row
        for value in informative_dates
        for row in _eligible_rows(rows_by_date.get(value, []))
    ]
    aggregate_frozen = _score(aggregate_rows, frozen_rule)
    aggregate_down = _score(aggregate_rows, lambda row: "down")
    aggregate_current = _score(aggregate_rows, lambda row: row.entry.prediction.direction)
    aggregate_lift = _lift(aggregate_frozen, aggregate_down)
    aggregate_positive = aggregate_lift is not None and aggregate_lift > 0.0

    promotion_gate_met = (
        len(positive_reports) >= REQUIRED_POSITIVE_INDEPENDENT_SESSIONS
        and aggregate_positive
    )

    if promotion_gate_met:
        status = "eligible_for_shadow_experiment_review"
    elif not independent_reports:
        status = "awaiting_independent_sessions"
    elif not informative_reports:
        status = "awaiting_informative_sessions"
    else:
        status = "collecting_independent_evidence"

    selection_resolved = sum(resolved_by_date.get(value, 0) for value in selection_dates)
    return {
        "status": status,
        "hypothesis_id": HYPOTHESIS_ID,
        "selection_session": SELECTION_SESSION.isoformat(),
        "selection_or_earlier_resolved_5m_rows_excluded": selection_resolved,
        "horizon_minutes": HORIZON_MINUTES,
        "regime": REGIME,
        "frozen_rule": {
            "local_gex_slope_gt_0": "down",
            "local_gex_slope_lt_0": "up",
            "zero_or_missing": "unscored",
        },
        "journal": str(journal_path),
        "log_paths": [str(path) for path in log_paths],
        "feature_observations": len(observations),
        "matched_resolved_rows_all_horizons": len(rows),
        "independent_sessions": independent_reports,
        "promotion_gate": {
            "minimum_matched_5m_rows_per_informative_session": MIN_MATCHED_5M_ROWS,
            "required_positive_independent_sessions": REQUIRED_POSITIVE_INDEPENDENT_SESSIONS,
            "independent_session_count": len(independent_reports),
            "informative_session_count": len(informative_reports),
            "positive_lift_session_count": len(positive_reports),
            "aggregate": {
                "frozen_rule": aggregate_frozen,
                "always_down": aggregate_down,
                "current_prediction": aggregate_current,
                "lift_vs_always_down": aggregate_lift,
                "positive_lift": aggregate_positive,
            },
            "met": promotion_gate_met,
        },
        "production_predictor_change_authorized": False,
        "execution_authorized": False,
        "next_action": (
            "Review a separate shadow-model experiment; this report does not authorize production or execution."
            if promotion_gate_met
            else "Continue collecting independent sessions without changing the frozen v1 rule."
        ),
        "guardrails": [
            "The 2026-08-14 selection session and any earlier rows are excluded from the independent promotion gate.",
            "Always-down is scored on the same negative-gamma rows where the frozen slope rule is scorable.",
            "All informative independent sessions are included in the aggregate, including sessions with negative lift.",
            "This report is research-only and cannot enable trading or alter the production predictor.",
        ],
    }
