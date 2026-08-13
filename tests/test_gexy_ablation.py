from dataclasses import replace
from datetime import datetime, timedelta, timezone

from packages.gexy.ablation import evaluate_regime_ablation
from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow


def _row(i: int) -> ResearchRow:
    regime = -1.0 if i % 2 == 0 else 1.0
    move = -2.0 if regime < 0 else 2.0
    return ResearchRow(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i),
        spot=6000.0 + i,
        spot_change=0.0,
        iv_change=0.0,
        total_gex=0.0,
        gamma_change=0.0,
        vanna_component=0.0,
        charm_component=0.0,
        estimated_hedge_demand=0.0,
        positioning_confidence=1.0,
        label=make_label(6000.0, 6000.0 + move, 5),
        regime_score=regime,
    )


def test_regime_ablation_preserves_split_and_reports_improvement():
    rows = [_row(i) for i in range(60)]
    result = evaluate_regime_ablation(rows)
    assert result.with_regime.train_samples == result.without_regime.train_samples
    assert result.with_regime.validation_samples == result.without_regime.validation_samples
    assert result.with_regime.test_samples == result.without_regime.test_samples
    assert result.improvement.mean_absolute_error > 0


def test_zero_regime_has_zero_ablation_delta():
    rows = [replace(_row(i), regime_score=0.0) for i in range(60)]
    result = evaluate_regime_ablation(rows)
    assert result.improvement.directional_accuracy == 0.0
    assert result.improvement.mean_absolute_error == 0.0
    assert result.improvement.mean_bias_absolute == 0.0
    assert result.improvement.brier_score == 0.0
