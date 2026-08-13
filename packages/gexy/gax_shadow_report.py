from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .gax_shadow_journal import load_gax_shadows, summarize_gax_shadow
from .prediction_journal import load_entries


DEFAULT_MIN_RESOLVED = 200
DEFAULT_MIN_ALIGNMENT = 0.55
DEFAULT_MIN_HORIZON_RESOLVED = 50
DEFAULT_REQUIRED_HORIZONS = (5, 15, 30, 60)


def _promotion_recommendation(
    report: dict[str, object],
    *,
    min_resolved: int = DEFAULT_MIN_RESOLVED,
    min_alignment: float = DEFAULT_MIN_ALIGNMENT,
    min_horizon_resolved: int = DEFAULT_MIN_HORIZON_RESOLVED,
) -> dict[str, object]:
    overall = report["overall"]
    by_horizon = report["by_horizon"]
    assert isinstance(overall, dict)
    assert isinstance(by_horizon, dict)

    resolved = int(overall.get("resolved", 0))
    alignment = float(overall.get("bias_alignment_accuracy", 0.0))
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
    }
    report["promotion_recommendation"] = _promotion_recommendation(report)
    return report
