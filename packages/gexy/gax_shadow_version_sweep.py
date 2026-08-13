from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .gax_shadow_candidate import score_shadow_candidate
from .gax_shadow_journal import GAXShadowRecord, load_gax_shadows
from .prediction_journal import PredictionJournalEntry, load_entries


DEFAULT_SHADOW_THRESHOLDS = (0.0, 0.5, 1.0, 2.0)
DEFAULT_MIN_CANDIDATE_RESOLVED = 100
DEFAULT_MIN_CANDIDATE_OVERRIDES = 25
DEFAULT_MIN_CANDIDATE_LIFT = 0.01


def build_shadow_candidate_sweep_by_model_version(
    entries: Iterable[PredictionJournalEntry],
    shadows: Iterable[GAXShadowRecord],
) -> dict[str, dict[str, dict[str, object]]]:
    entry_list = list(entries)
    shadow_list = list(shadows)
    versions = sorted({shadow.model_version for shadow in shadow_list})
    report: dict[str, dict[str, dict[str, object]]] = {}

    for version in versions:
        version_entries = [entry for entry in entry_list if entry.model_version == version]
        version_shadows = [shadow for shadow in shadow_list if shadow.model_version == version]
        report[version] = {
            str(threshold): asdict(
                score_shadow_candidate(
                    version_entries,
                    version_shadows,
                    min_gax_magnitude=threshold,
                )
            )
            for threshold in DEFAULT_SHADOW_THRESHOLDS
        }

    return report


def select_best_shadow_candidate(
    sweep: dict[str, dict[str, object]],
    *,
    min_resolved: int = DEFAULT_MIN_CANDIDATE_RESOLVED,
    min_overrides: int = DEFAULT_MIN_CANDIDATE_OVERRIDES,
    min_lift: float = DEFAULT_MIN_CANDIDATE_LIFT,
) -> dict[str, object]:
    """Recommend a shadow threshold only when evidence is sufficient.

    This selector is advisory only. It never changes production behavior.
    Ties prefer the larger threshold, which is the more conservative override rule.
    """
    eligible: list[tuple[float, float, dict[str, object]]] = []
    for threshold_text, metrics in sweep.items():
        resolved = int(metrics.get("resolved", 0))
        overrides = int(metrics.get("overrides", 0))
        lift = float(metrics.get("lift", 0.0))
        if resolved >= min_resolved and overrides >= min_overrides and lift >= min_lift:
            threshold = float(threshold_text)
            eligible.append((lift, threshold, metrics))

    if not eligible:
        return {
            "recommended": False,
            "reason": "no_shadow_candidate_clears_evidence_gate",
            "min_resolved": min_resolved,
            "min_overrides": min_overrides,
            "min_lift": min_lift,
        }

    lift, threshold, metrics = max(eligible, key=lambda item: (item[0], item[1]))
    return {
        "recommended": True,
        "reason": "shadow_candidate_clears_evidence_gate",
        "threshold": threshold,
        "resolved": int(metrics.get("resolved", 0)),
        "overrides": int(metrics.get("overrides", 0)),
        "production_accuracy": float(metrics.get("production_accuracy", 0.0)),
        "candidate_accuracy": float(metrics.get("candidate_accuracy", 0.0)),
        "lift": lift,
        "min_resolved": min_resolved,
        "min_overrides": min_overrides,
        "min_lift": min_lift,
    }


def build_consolidated_shadow_v2_report(
    prediction_journal: str | Path,
    gax_shadow_journal: str | Path,
) -> dict[str, object]:
    """Compose the existing GAX shadow report with per-version v2 sweeps.

    This is read-only evaluation. It never changes production predictions or
    promotes GAX into the live model.
    """
    from .gax_shadow_report import build_gax_shadow_report

    entries = load_entries(prediction_journal)
    shadows = load_gax_shadows(gax_shadow_journal)
    report = build_gax_shadow_report(prediction_journal, gax_shadow_journal)
    by_version = build_shadow_candidate_sweep_by_model_version(entries, shadows)
    report["shadow_candidate_threshold_sweep_by_model_version"] = by_version
    report["shadow_candidate_recommendation"] = select_best_shadow_candidate(
        report["shadow_candidate_threshold_sweep"]
    )
    report["shadow_candidate_recommendation_by_model_version"] = {
        version: select_best_shadow_candidate(sweep)
        for version, sweep in by_version.items()
    }
    return report
