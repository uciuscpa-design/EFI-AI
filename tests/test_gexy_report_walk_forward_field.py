from packages.gexy.gax_shadow_report import build_gax_shadow_report


def test_report_exposes_walk_forward_horizon_readiness(tmp_path) -> None:
    predictions = tmp_path / "predictions.jsonl"
    shadows = tmp_path / "gax.jsonl"

    report = build_gax_shadow_report(predictions, shadows)

    decision = report["shortest_walk_forward_validated_horizon"]
    assert decision["recommended"] is False
    assert decision["reason"] == "no_horizon_clears_walk_forward_gate"
    assert decision["automatic_promotion"] is False
