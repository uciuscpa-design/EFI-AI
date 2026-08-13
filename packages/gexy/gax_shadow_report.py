from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .gax_shadow_journal import index_gax_shadows, load_gax_shadows, summarize_gax_shadow
from .prediction_journal import load_entries


DEFAULT_MIN_RESOLVED = 200
DEFAULT_MIN_ALIGNMENT = 0.55
DEFAULT_MIN_HORIZON_RESOLVED = 50
DEFAULT_REQUIRED_HORIZONS = (5, 15, 30, 60)
DEFAULT_MIN_DISAGREEMENTS = 50
DEFAULT_MIN_GAX_WIN_RATE_ON_DISAGREEMENT = 0.55


def _direction_from_move(move: float) -> str:
    if move > 1e-9:
        return "up"
    if move < -1e-9:
        return "down"
    return "flat"


def _incremental_value(entries, shadows) -> dict[str, object]:
    shadow_index = index_gax_shadows(shadows)
    paired = [
        (entry, shadow_index[entry.prediction_id])
        for entry in entries
        if entry.resolved and entry.prediction_id in shadow_index
    ]
    if not paired:
        return {
            "paired_resolved": 0,
            "production_directional_accuracy": 0.0,
            "gax_directional_accuracy": 0.0,
            "agreement_count": 0,
            "agreement_accuracy": 0.0,
            "disagreement_count": 0,
            "gax_win_rate_on_disagreement": 0.0,
        }

    production_hits = 0
    gax_hits = 0
    agreement_count = 0
    agreement_hits = 0
    disagreement_count = 0
    gax_disagreement_wins = 0

    for entry, shadow in paired:
        realized_direction = _direction_from_move(float(entry.realized_move_points or 0.0))
        production_direction = entry.prediction.direction
        gax_direction = shadow.features.acceleration_bias
        production_hit = production_direction == realized_direction
        gax_hit = gax_direction == realized_direction
        production_hits += int(production_hit)
        gax_hits += int(gax_hit)

        if production_direction == gax_direction:
            agreement_count += 1
            agreement_hits += int(production_hit)
        else:
            disagreement_count += 1
            if gax_hit and not production_hit:
                gax_disagreement_wins += 1

    return {
        "paired_resolved": len(paired),
        "production_directional_accuracy": production_hits / len(paired),
        "gax_directional_accuracy": gax_hits / len(paired),
        "agreement_count": agreement_count,
        "agreement_accuracy": agreement_hits / agreement_count if agreement_count else 0.0,
        "disagreement_count": disagreement_count,
        "gax_win_rate_on_disagreement": (
            gax_disagreement_wins / disagreement_count if disagreement_count else 0.0
        ),
    }


def _promotion_recommendation(
    report: dict[str, object],
    *,
    min_resolved: int = DEFAULT_MIN_RESOLVED,
    min_alignment: float = DEFAULT_MIN_ALIGNMENT,
    min_horizon_resolved: int = DEFAULT_MIN_HORIZON_RESOLVED,
    min_disagreements: int = DEFAULT_MIN_DISAGREEMENTS,
    min_gax_win_rate_on_disagreement: float = DEFAULT_MIN_GAX_WIN_RATE_ON_DISAGREEMENT,
) -> dict[str, object]:
    overall = report["overall"]
    by_horizon = report["by_horizon"]
    incremental = report["incremental_value"]
    assert isinstance(overall, dict)
    assert isinstance(by_horizon, dict)
    assert isinstance(incremental, dict)

    resolved = int(overall.get("resolved", 0))
    alignment = float(overall.get("bias_alignment_accuracy", 0.0))
    disagreement_count = int(incremental.get("disagreement_count", 0))
    gax_win_rate = float(incremental.get("gax_win_rate_on_disagreement", 0.0))
    horizon_checks: dict[str, bool] = {}
    for horizon in DEFAULT_REQUIRED_HORIZONS:
        metrics = by_horizon.get(str(horizon), {})
        if not isinstance(metrics, dict):
            metrics = {}
        horizon_checks[str(horizon)] = (
            int(metrics.get("resolved", 0)) >= min_horizon_resolved
            and float(metrics.get("bias_alignment_accuracy", 0.0)) >= min_alignment
        )

    if resolved < min_resolved:
        reason = "insufficient_overall_samples"
        eligible = False
    elif alignment < min_alignment:
        reason = "insufficient_overall_alignment"
        eligible = False
    elif not all(horizon_checks.values()):
        reason = "insufficient_horizon_evidence"
        eligible = False
    elif disagreement_count < min_disagreements:
        reason = "insufficient_incremental_disagreement_samples"
        eligible = False
    elif gax_win_rate < min_gax_win_rate_on_disagreement:
        reason = "insufficient_incremental_lift"
        eligible = False
    else:
        reason = "shadow_evidence_clears_promotion_gate"
        eligible = True

    return {
        "eligible": eligible,
        "reason": reason,
        "resolved": resolved,
        "alignment_accuracy": alignment,
        "min_resolved": min_resolved,
        "min_alignment": min_alignment,
        "min_horizon_resolved": min_horizon_resolved,
        "horizon_checks": horizon_checks,
        "disagreement_count": disagreement_count,
        "gax_win_rate_on_disagreement": gax_win_rate,
        "min_disagreements": min_disagreements,
        "min_gax_win_rate_on_disagreement": min_gax_win_rate_on_disagreement,
    }


def build_gax_shadow_report(
    prediction_journal: str | Path,
    gax_shadow_journal: str | Path,
) -> dict[str, object]:
    entries = load_entries(prediction_journal)
    shadows = load_gax_shadows(gax_shadow_journal)

    overall = summarize_gax_shadow(entries, shadows)
    horizons = sorted({shadow.horizon_minutes for shadow in shadows})
    versions = sorted({shadow.model_version for shadow in shadows})

    by_horizon: dict[str, dict[str, object]] = {}
    for horizon in horizons:
        horizon_entries = [
            entry for entry in entries if entry.prediction.horizon_minutes == horizon
        ]
        horizon_shadows = [
            shadow for shadow in shadows if shadow.horizon_minutes == horizon
        ]
        by_horizon[str(horizon)] = asdict(
            summarize_gax_shadow(horizon_entries, horizon_shadows)
        )

    by_model_version: dict[str, dict[str, object]] = {}
    for version in versions:
        version_entries = [entry for entry in entries if entry.model_version == version]
        version_shadows = [shadow for shadow in shadows if shadow.model_version == version]
        by_model_version[version] = asdict(
            summarize_gax_shadow(version_entries, version_shadows)
        )

    report: dict[str, object] = {
        "prediction_journal_path": str(Path(prediction_journal)),
        "gax_shadow_journal_path": str(Path(gax_shadow_journal)),
        "overall": asdict(overall),
        "by_horizon": by_horizon,
        "by_model_version": by_model_version,
        "incremental_value": _incremental_value(entries, shadows),
    }
    report["promotion_recommendation"] = _promotion_recommendation(report)
    return report
