from packages.gexy.gax_shadow_report import select_shortest_trusted_horizon


def test_shortest_trusted_horizon_picks_smallest_passing_horizon() -> None:
    by_horizon = {
        "1": {"resolved": 120, "bias_alignment_accuracy": 0.68},
        "2": {"resolved": 120, "bias_alignment_accuracy": 0.71},
        "3": {"resolved": 150, "bias_alignment_accuracy": 0.80},
    }

    decision = select_shortest_trusted_horizon(by_horizon)

    assert decision["recommended"] is True
    assert decision["horizon_minutes"] == 2
    assert decision["success_rate"] == 0.71
    assert decision["automatic_promotion"] is False


def test_shortest_trusted_horizon_returns_none_when_evidence_is_too_weak() -> None:
    by_horizon = {
        "1": {"resolved": 99, "bias_alignment_accuracy": 0.95},
        "2": {"resolved": 120, "bias_alignment_accuracy": 0.69},
    }

    decision = select_shortest_trusted_horizon(by_horizon)

    assert decision["recommended"] is False
    assert decision["reason"] == "no_horizon_clears_trust_gate"
