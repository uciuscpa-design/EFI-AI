from datetime import datetime, timedelta, timezone

from packages.gexy.gax_features import GAXFeatures
from packages.gexy.gax_shadow_candidate import score_shadow_candidate
from packages.gexy.gax_shadow_journal import append_gax_shadow, make_gax_shadow_record
from packages.gexy.gax_shadow_report import _promotion_recommendation, build_gax_shadow_report
from packages.gexy.gax_shadow_version_sweep import (
    build_consolidated_shadow_v2_report,
    build_shadow_candidate_sweep_by_model_version,
    select_best_shadow_candidate,
    validate_shadow_candidate_out_of_sample,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import append_entry, make_entry, resolve_entry, rewrite_entries


def _prediction(horizon: int, direction: str = "up") -> LivePrediction:
    return LivePrediction(
        direction=direction,
        expected_move_points=4.0 if direction == "up" else -4.0,
        primary_target=7754.0 if direction == "up" else 7746.0,
        invalidation_level=7735.0,
        confidence=0.6,
        horizon_minutes=horizon,
        regime="positive_gamma_mean_reversion",
    )


def test_gax_shadow_report_groups_by_horizon_and_model_version(tmp_path) -> None:
    predictions = tmp_path / "predictions.jsonl"
    shadows = tmp_path / "gax.jsonl"
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    features = GAXFeatures(
        spot=7750.0,
        local_gax=2.0,
        local_gax_curvature=0.5,
        magnitude=2.0,
        acceleration_bias="up",
    )

    entries = []
    shadow_records = []
    for horizon, version in ((5, "gexy-live-v1"), (15, "gexy-live-v2-shadow")):
        entry = make_entry(
            created_at=t0,
            spot=7750.0,
            prediction=_prediction(horizon),
            model_version=version,
        )
        append_entry(predictions, entry)
        shadow = make_gax_shadow_record(
            prediction_id=entry.prediction_id,
            created_at=t0,
            horizon_minutes=horizon,
            model_version=version,
            features=features,
        )
        append_gax_shadow(shadows, shadow)
        shadow_records.append(shadow)
        entries.append(resolve_entry(entry, resolved_at=entry.due_at, realized_spot=7752.0))

    rewrite_entries(predictions, entries)
    report = build_gax_shadow_report(predictions, shadows)

    assert report["overall"]["resolved"] == 2
    assert report["overall"]["bias_alignment_accuracy"] == 1.0
    assert set(report["by_horizon"]) == {"5", "15"}
    assert set(report["by_model_version"]) == {"gexy-live-v1", "gexy-live-v2-shadow"}
    assert report["by_horizon"]["5"]["resolved"] == 1
    assert report["by_model_version"]["gexy-live-v2-shadow"]["mean_magnitude"] == 2.0
    assert report["incremental_value"]["paired_resolved"] == 2
    assert report["incremental_value"]["agreement_count"] == 2
    assert report["incremental_value"]["disagreement_count"] == 0
    assert set(report["shadow_candidate_threshold_sweep"]) == {"0.0", "0.5", "1.0", "2.0"}
    assert all(metrics["lift"] == 0.0 for metrics in report["shadow_candidate_threshold_sweep"].values())

    by_horizon = report["shadow_candidate_threshold_sweep_by_horizon"]
    assert set(by_horizon) == {"5", "15"}
    assert all(set(metrics) == {"0.0", "0.5", "1.0", "2.0"} for metrics in by_horizon.values())
    assert all(
        threshold_metrics["resolved"] == 1
        for horizon_metrics in by_horizon.values()
        for threshold_metrics in horizon_metrics.values()
    )

    by_version = build_shadow_candidate_sweep_by_model_version(entries, shadow_records)
    assert set(by_version) == {"gexy-live-v1", "gexy-live-v2-shadow"}
    assert all(set(metrics) == {"0.0", "0.5", "1.0", "2.0"} for metrics in by_version.values())
    assert all(
        threshold_metrics["resolved"] == 1
        for version_metrics in by_version.values()
        for threshold_metrics in version_metrics.values()
    )

    consolidated = build_consolidated_shadow_v2_report(predictions, shadows)
    assert set(consolidated["shadow_candidate_threshold_sweep_by_model_version"]) == {
        "gexy-live-v1",
        "gexy-live-v2-shadow",
    }
    assert consolidated["overall"]["resolved"] == report["overall"]["resolved"]
    assert consolidated["promotion_recommendation"] == report["promotion_recommendation"]
    assert consolidated["shadow_candidate_recommendation"]["recommended"] is False
    assert all(
        recommendation["recommended"] is False
        for recommendation in consolidated["shadow_candidate_recommendation_by_model_version"].values()
    )
    assert consolidated["shadow_candidate_out_of_sample"]["validated"] is False

    assert report["promotion_recommendation"]["eligible"] is False
    assert report["promotion_recommendation"]["reason"] == "insufficient_overall_samples"


def test_shadow_candidate_selector_requires_samples_overrides_and_lift() -> None:
    weak = {
        "0.0": {
            "resolved": 99,
            "overrides": 30,
            "production_accuracy": 0.50,
            "candidate_accuracy": 0.60,
            "lift": 0.10,
        }
    }
    decision = select_best_shadow_candidate(weak)
    assert decision["recommended"] is False

    sweep = {
        "0.5": {
            "resolved": 120,
            "overrides": 30,
            "production_accuracy": 0.50,
            "candidate_accuracy": 0.53,
            "lift": 0.03,
        },
        "1.0": {
            "resolved": 120,
            "overrides": 25,
            "production_accuracy": 0.50,
            "candidate_accuracy": 0.53,
            "lift": 0.03,
        },
        "2.0": {
            "resolved": 120,
            "overrides": 20,
            "production_accuracy": 0.50,
            "candidate_accuracy": 0.55,
            "lift": 0.05,
        },
    }
    decision = select_best_shadow_candidate(sweep)
    assert decision["recommended"] is True
    assert decision["threshold"] == 1.0
    assert decision["lift"] == 0.03


def test_shadow_candidate_out_of_sample_uses_later_unseen_block() -> None:
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    features = GAXFeatures(
        spot=7750.0,
        local_gax=2.0,
        local_gax_curvature=0.5,
        magnitude=2.0,
        acceleration_bias="up",
    )
    entries = []
    shadows = []
    for offset in range(4):
        created_at = t0 + timedelta(minutes=offset * 10)
        entry = make_entry(
            created_at=created_at,
            spot=7750.0,
            prediction=_prediction(5, "down"),
        )
        entries.append(resolve_entry(entry, resolved_at=entry.due_at, realized_spot=7752.0))
        shadows.append(
            make_gax_shadow_record(
                prediction_id=entry.prediction_id,
                created_at=created_at,
                horizon_minutes=5,
                model_version=entry.model_version,
                features=features,
            )
        )

    result = validate_shadow_candidate_out_of_sample(
        entries,
        shadows,
        train_fraction=0.5,
        min_train_resolved=2,
        min_train_overrides=2,
        min_train_lift=0.01,
        min_validation_resolved=2,
    )
    assert result["validated"] is True
    assert result["train_resolved"] == 2
    assert result["validation_resolved"] == 2
    assert result["threshold"] == 2.0
    assert result["validation_metrics"]["production_accuracy"] == 0.0
    assert result["validation_metrics"]["candidate_accuracy"] == 1.0
    assert result["validation_metrics"]["lift"] == 1.0
    assert result["validation_positive_lift"] is True


def test_gax_promotion_requires_horizon_and_incremental_evidence() -> None:
    report = {
        "overall": {"resolved": 250, "bias_alignment_accuracy": 0.60},
        "by_horizon": {
            str(horizon): {"resolved": 60, "bias_alignment_accuracy": 0.58}
            for horizon in (5, 15, 30, 60)
        },
        "incremental_value": {
            "disagreement_count": 60,
            "gax_win_rate_on_disagreement": 0.60,
        },
    }
    decision = _promotion_recommendation(report)
    assert decision["eligible"] is True
    assert decision["reason"] == "shadow_evidence_clears_promotion_gate"

    report["by_horizon"]["60"]["resolved"] = 49
    decision = _promotion_recommendation(report)
    assert decision["eligible"] is False
    assert decision["reason"] == "insufficient_horizon_evidence"

    report["by_horizon"]["60"]["resolved"] = 60
    report["incremental_value"]["disagreement_count"] = 49
    decision = _promotion_recommendation(report)
    assert decision["eligible"] is False
    assert decision["reason"] == "insufficient_incremental_disagreement_samples"

    report["incremental_value"]["disagreement_count"] = 60
    report["incremental_value"]["gax_win_rate_on_disagreement"] = 0.54
    decision = _promotion_recommendation(report)
    assert decision["eligible"] is False
    assert decision["reason"] == "insufficient_incremental_lift"


def test_shadow_candidate_measures_lift_without_changing_production() -> None:
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(created_at=t0, spot=7750.0, prediction=_prediction(5, "down"))
    resolved = resolve_entry(entry, resolved_at=entry.due_at, realized_spot=7752.0)
    shadow = make_gax_shadow_record(
        prediction_id=entry.prediction_id,
        created_at=t0,
        horizon_minutes=5,
        model_version=entry.model_version,
        features=GAXFeatures(
            spot=7750.0,
            local_gax=2.0,
            local_gax_curvature=0.5,
            magnitude=2.0,
            acceleration_bias="up",
        ),
    )

    metrics = score_shadow_candidate([resolved], [shadow])
    assert metrics.resolved == 1
    assert metrics.overrides == 1
    assert metrics.production_accuracy == 0.0
    assert metrics.candidate_accuracy == 1.0
    assert metrics.lift == 1.0


def test_shadow_candidate_respects_magnitude_threshold() -> None:
    t0 = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(created_at=t0, spot=7750.0, prediction=_prediction(5, "down"))
    resolved = resolve_entry(entry, resolved_at=entry.due_at, realized_spot=7748.0)
    shadow = make_gax_shadow_record(
        prediction_id=entry.prediction_id,
        created_at=t0,
        horizon_minutes=5,
        model_version=entry.model_version,
        features=GAXFeatures(
            spot=7750.0,
            local_gax=0.2,
            local_gax_curvature=0.1,
            magnitude=0.2,
            acceleration_bias="up",
        ),
    )

    metrics = score_shadow_candidate([resolved], [shadow], min_gax_magnitude=1.0)
    assert metrics.overrides == 0
    assert metrics.production_accuracy == 1.0
    assert metrics.candidate_accuracy == 1.0
    assert metrics.lift == 0.0
