from packages.gexy.gax_shadow_version_sweep import summarize_promotion_readiness


def _base_report() -> dict[str, object]:
    return {
        "shadow_candidate_recommendation": {"recommended": False},
        "shadow_candidate_out_of_sample": {
            "validated": False,
            "validation_positive_lift": False,
        },
        "shadow_candidate_walk_forward": {"stable": False},
        "shadow_candidate_recommendation_by_model_version": {},
        "shadow_candidate_forward_validation_by_regime": {},
    }


def test_promotion_readiness_not_ready_without_global_candidate() -> None:
    decision = summarize_promotion_readiness(_base_report())
    assert decision["status"] == "not_ready"
    assert decision["reason"] == "no_global_shadow_candidate"
    assert decision["automatic_promotion"] is False


def test_promotion_readiness_shadow_ready_when_forward_gates_remain() -> None:
    report = _base_report()
    report["shadow_candidate_recommendation"] = {"recommended": True}
    decision = summarize_promotion_readiness(report)
    assert decision["status"] == "shadow_ready"
    assert decision["automatic_promotion"] is False


def test_promotion_readiness_requires_manual_review_after_all_gates_clear() -> None:
    report = _base_report()
    report["shadow_candidate_recommendation"] = {"recommended": True}
    report["shadow_candidate_out_of_sample"] = {
        "validated": True,
        "validation_positive_lift": True,
    }
    report["shadow_candidate_walk_forward"] = {"stable": True}
    report["shadow_candidate_recommendation_by_model_version"] = {
        "gexy-live-v2-shadow": {"recommended": True}
    }
    report["shadow_candidate_forward_validation_by_regime"] = {
        "negative_gamma_expansion": {"walk_forward": {"stable": True}},
        "positive_gamma_mean_reversion": {"walk_forward": {"stable": True}},
    }

    decision = summarize_promotion_readiness(report)
    assert decision["status"] == "eligible_for_manual_v2_review"
    assert decision["reason"] == "all_advisory_shadow_gates_cleared"
    assert decision["automatic_promotion"] is False
