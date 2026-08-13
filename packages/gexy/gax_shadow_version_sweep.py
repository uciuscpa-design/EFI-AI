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
DEFAULT_TRAIN_FRACTION = 0.70
DEFAULT_MIN_VALIDATION_RESOLVED = 50
DEFAULT_WALK_FORWARD_FOLDS = 3
DEFAULT_MIN_MEAN_FORWARD_LIFT = 0.01


def _score_sweep(entries: Iterable[PredictionJournalEntry], shadows: Iterable[GAXShadowRecord]) -> dict[str, dict[str, object]]:
    entry_list = list(entries)
    shadow_list = list(shadows)
    return {str(threshold): asdict(score_shadow_candidate(entry_list, shadow_list, min_gax_magnitude=threshold)) for threshold in DEFAULT_SHADOW_THRESHOLDS}


def build_shadow_candidate_sweep_by_model_version(entries: Iterable[PredictionJournalEntry], shadows: Iterable[GAXShadowRecord]) -> dict[str, dict[str, dict[str, object]]]:
    entry_list = list(entries)
    shadow_list = list(shadows)
    report = {}
    for version in sorted({shadow.model_version for shadow in shadow_list}):
        report[version] = _score_sweep([entry for entry in entry_list if entry.model_version == version], [shadow for shadow in shadow_list if shadow.model_version == version])
    return report


def build_shadow_candidate_sweep_by_regime(entries: Iterable[PredictionJournalEntry], shadows: Iterable[GAXShadowRecord]) -> dict[str, dict[str, dict[str, object]]]:
    entry_list = list(entries)
    shadow_by_id = {shadow.prediction_id: shadow for shadow in shadows}
    report = {}
    for regime in sorted({entry.prediction.regime for entry in entry_list}):
        regime_entries = [entry for entry in entry_list if entry.prediction.regime == regime]
        regime_ids = {entry.prediction_id for entry in regime_entries}
        report[regime] = _score_sweep(regime_entries, [shadow for prediction_id, shadow in shadow_by_id.items() if prediction_id in regime_ids])
    return report


def select_best_shadow_candidate(sweep: dict[str, dict[str, object]], *, min_resolved: int = DEFAULT_MIN_CANDIDATE_RESOLVED, min_overrides: int = DEFAULT_MIN_CANDIDATE_OVERRIDES, min_lift: float = DEFAULT_MIN_CANDIDATE_LIFT) -> dict[str, object]:
    eligible = []
    for threshold_text, metrics in sweep.items():
        resolved = int(metrics.get("resolved", 0)); overrides = int(metrics.get("overrides", 0)); lift = float(metrics.get("lift", 0.0))
        if resolved >= min_resolved and overrides >= min_overrides and lift >= min_lift:
            eligible.append((lift, float(threshold_text), metrics))
    if not eligible:
        return {"recommended": False, "reason": "no_shadow_candidate_clears_evidence_gate", "min_resolved": min_resolved, "min_overrides": min_overrides, "min_lift": min_lift}
    lift, threshold, metrics = max(eligible, key=lambda item: (item[0], item[1]))
    return {"recommended": True, "reason": "shadow_candidate_clears_evidence_gate", "threshold": threshold, "resolved": int(metrics.get("resolved", 0)), "overrides": int(metrics.get("overrides", 0)), "production_accuracy": float(metrics.get("production_accuracy", 0.0)), "candidate_accuracy": float(metrics.get("candidate_accuracy", 0.0)), "lift": lift, "min_resolved": min_resolved, "min_overrides": min_overrides, "min_lift": min_lift}


def _paired_resolved_entries(entries, shadows):
    shadow_by_id = {shadow.prediction_id: shadow for shadow in shadows}
    paired_entries = sorted((entry for entry in entries if entry.resolved and entry.prediction_id in shadow_by_id), key=lambda entry: entry.created_at)
    return paired_entries, shadow_by_id


def _candidate_sweep(entries, shadow_by_id):
    ids = {entry.prediction_id for entry in entries}
    return _score_sweep(entries, [shadow for prediction_id, shadow in shadow_by_id.items() if prediction_id in ids])


def validate_shadow_candidate_out_of_sample(entries, shadows, *, train_fraction=DEFAULT_TRAIN_FRACTION, min_train_resolved=DEFAULT_MIN_CANDIDATE_RESOLVED, min_train_overrides=DEFAULT_MIN_CANDIDATE_OVERRIDES, min_train_lift=DEFAULT_MIN_CANDIDATE_LIFT, min_validation_resolved=DEFAULT_MIN_VALIDATION_RESOLVED):
    if not 0.0 < train_fraction < 1.0: raise ValueError("train_fraction must be between 0 and 1")
    paired_entries, shadow_by_id = _paired_resolved_entries(entries, shadows)
    if len(paired_entries) < 2: return {"validated": False, "reason": "insufficient_paired_resolved_samples", "paired_resolved": len(paired_entries)}
    split_index = max(1, min(int(len(paired_entries) * train_fraction), len(paired_entries) - 1)); train_entries = paired_entries[:split_index]; validation_entries = paired_entries[split_index:]
    selection = select_best_shadow_candidate(_candidate_sweep(train_entries, shadow_by_id), min_resolved=min_train_resolved, min_overrides=min_train_overrides, min_lift=min_train_lift)
    if not selection.get("recommended"): return {"validated": False, "reason": "no_training_candidate", "train_resolved": len(train_entries), "validation_resolved": len(validation_entries), "training_selection": selection}
    if len(validation_entries) < min_validation_resolved: return {"validated": False, "reason": "insufficient_validation_samples", "train_resolved": len(train_entries), "validation_resolved": len(validation_entries), "training_selection": selection, "min_validation_resolved": min_validation_resolved}
    threshold = float(selection["threshold"]); validation_ids = {entry.prediction_id for entry in validation_entries}; validation_shadows = [shadow for prediction_id, shadow in shadow_by_id.items() if prediction_id in validation_ids]
    metrics = asdict(score_shadow_candidate(validation_entries, validation_shadows, min_gax_magnitude=threshold))
    return {"validated": True, "reason": "candidate_scored_on_unseen_validation_block", "train_resolved": len(train_entries), "validation_resolved": len(validation_entries), "threshold": threshold, "training_selection": selection, "validation_metrics": metrics, "validation_positive_lift": float(metrics.get("lift", 0.0)) > 0.0}


def validate_shadow_candidate_walk_forward(entries, shadows, *, folds=DEFAULT_WALK_FORWARD_FOLDS, min_train_resolved=DEFAULT_MIN_CANDIDATE_RESOLVED, min_train_overrides=DEFAULT_MIN_CANDIDATE_OVERRIDES, min_train_lift=DEFAULT_MIN_CANDIDATE_LIFT, min_validation_resolved=DEFAULT_MIN_VALIDATION_RESOLVED, min_mean_forward_lift=DEFAULT_MIN_MEAN_FORWARD_LIFT):
    if folds < 2: raise ValueError("folds must be at least 2")
    paired_entries, shadow_by_id = _paired_resolved_entries(entries, shadows); minimum_total = min_train_resolved + folds * min_validation_resolved
    if len(paired_entries) < minimum_total: return {"validated": False, "stable": False, "reason": "insufficient_samples_for_walk_forward", "paired_resolved": len(paired_entries), "min_required": minimum_total, "folds_requested": folds}
    validation_block = min_validation_resolved; first_validation_start = len(paired_entries) - folds * validation_block; results = []
    for fold_index in range(folds):
        start = first_validation_start + fold_index * validation_block; end = start + validation_block; train_entries = paired_entries[:start]; validation_entries = paired_entries[start:end]
        selection = select_best_shadow_candidate(_candidate_sweep(train_entries, shadow_by_id), min_resolved=min_train_resolved, min_overrides=min_train_overrides, min_lift=min_train_lift)
        if not selection.get("recommended"):
            results.append({"fold": fold_index + 1, "validated": False, "reason": "no_training_candidate", "train_resolved": len(train_entries), "validation_resolved": len(validation_entries), "training_selection": selection}); continue
        threshold = float(selection["threshold"]); ids = {entry.prediction_id for entry in validation_entries}; validation_shadows = [shadow for prediction_id, shadow in shadow_by_id.items() if prediction_id in ids]; metrics = asdict(score_shadow_candidate(validation_entries, validation_shadows, min_gax_magnitude=threshold))
        results.append({"fold": fold_index + 1, "validated": True, "reason": "candidate_scored_on_forward_fold", "train_resolved": len(train_entries), "validation_resolved": len(validation_entries), "threshold": threshold, "training_selection": selection, "validation_metrics": metrics, "positive_lift": float(metrics.get("lift", 0.0)) > 0.0})
    validated = [r for r in results if r.get("validated")]; lifts = [float(r["validation_metrics"].get("lift", 0.0)) for r in validated if isinstance(r.get("validation_metrics"), dict)]; positive = sum(l > 0.0 for l in lifts); all_scored = len(validated) == folds; all_positive = bool(lifts) and positive == len(lifts); mean_lift = sum(lifts) / len(lifts) if lifts else 0.0; stable = all_scored and all_positive and mean_lift >= min_mean_forward_lift
    return {"validated": all_scored, "stable": stable, "reason": "walk_forward_stability_gate_cleared" if stable else ("all_walk_forward_folds_scored_but_stability_gate_failed" if all_scored else "one_or_more_walk_forward_folds_lacked_training_candidate"), "folds_requested": folds, "folds_scored": len(validated), "positive_lift_folds": positive, "mean_validation_lift": mean_lift, "min_mean_forward_lift": min_mean_forward_lift, "all_folds_positive_lift": all_positive, "folds": results}


def validate_shadow_candidate_by_regime(entries, shadows):
    entry_list = list(entries); shadow_by_id = {shadow.prediction_id: shadow for shadow in shadows}; report = {}
    for regime in sorted({entry.prediction.regime for entry in entry_list}):
        regime_entries = [entry for entry in entry_list if entry.prediction.regime == regime]; ids = {entry.prediction_id for entry in regime_entries}; regime_shadows = [shadow for prediction_id, shadow in shadow_by_id.items() if prediction_id in ids]
        report[regime] = {"out_of_sample": validate_shadow_candidate_out_of_sample(regime_entries, regime_shadows), "walk_forward": validate_shadow_candidate_walk_forward(regime_entries, regime_shadows)}
    return report


def summarize_promotion_readiness(report: dict[str, object]) -> dict[str, object]:
    """Return an advisory-only v2 readiness verdict. Never promotes production automatically."""
    global_rec = report.get("shadow_candidate_recommendation", {})
    holdout = report.get("shadow_candidate_out_of_sample", {})
    walk = report.get("shadow_candidate_walk_forward", {})
    version_recs = report.get("shadow_candidate_recommendation_by_model_version", {})
    regime_forward = report.get("shadow_candidate_forward_validation_by_regime", {})
    global_candidate = isinstance(global_rec, dict) and bool(global_rec.get("recommended"))
    holdout_positive = isinstance(holdout, dict) and bool(holdout.get("validated")) and bool(holdout.get("validation_positive_lift"))
    walk_stable = isinstance(walk, dict) and bool(walk.get("stable"))
    version_ready = bool(version_recs) and any(isinstance(v, dict) and bool(v.get("recommended")) for v in version_recs.values())
    regime_ready = bool(regime_forward) and all(isinstance(v, dict) and isinstance(v.get("walk_forward"), dict) and bool(v["walk_forward"].get("stable")) for v in regime_forward.values())
    if not global_candidate:
        status = "not_ready"; reason = "no_global_shadow_candidate"
    elif global_candidate and not (holdout_positive and walk_stable and version_ready and regime_ready):
        status = "shadow_ready"; reason = "candidate_exists_but_forward_or_segment_gates_remain"
    else:
        status = "eligible_for_manual_v2_review"; reason = "all_advisory_shadow_gates_cleared"
    return {"status": status, "reason": reason, "automatic_promotion": False, "global_candidate": global_candidate, "holdout_positive_lift": holdout_positive, "walk_forward_stable": walk_stable, "model_version_ready": version_ready, "all_regimes_walk_forward_stable": regime_ready}


def build_consolidated_shadow_v2_report(prediction_journal: str | Path, gax_shadow_journal: str | Path) -> dict[str, object]:
    from .gax_shadow_report import build_gax_shadow_report
    entries = load_entries(prediction_journal); shadows = load_gax_shadows(gax_shadow_journal); report = build_gax_shadow_report(prediction_journal, gax_shadow_journal)
    by_version = build_shadow_candidate_sweep_by_model_version(entries, shadows); by_regime = build_shadow_candidate_sweep_by_regime(entries, shadows)
    report["shadow_candidate_threshold_sweep_by_model_version"] = by_version; report["shadow_candidate_threshold_sweep_by_regime"] = by_regime
    report["shadow_candidate_recommendation"] = select_best_shadow_candidate(report["shadow_candidate_threshold_sweep"])
    report["shadow_candidate_recommendation_by_model_version"] = {version: select_best_shadow_candidate(sweep) for version, sweep in by_version.items()}
    report["shadow_candidate_recommendation_by_regime"] = {regime: select_best_shadow_candidate(sweep) for regime, sweep in by_regime.items()}
    report["shadow_candidate_out_of_sample"] = validate_shadow_candidate_out_of_sample(entries, shadows); report["shadow_candidate_walk_forward"] = validate_shadow_candidate_walk_forward(entries, shadows); report["shadow_candidate_forward_validation_by_regime"] = validate_shadow_candidate_by_regime(entries, shadows)
    report["promotion_readiness"] = summarize_promotion_readiness(report)
    return report
