from datetime import datetime, timezone

from packages.gexy.baselines import zero_move
from packages.gexy.experiments import run_experiment
from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow


def test_experiment_runner_scores_forecaster() -> None:
    label = make_label(6500, 6500, 5)
    row = ResearchRow(
        timestamp=datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc),
        spot=6500,
        spot_change=0,
        iv_change=0,
        total_gex=0,
        gamma_change=0,
        vanna_component=0,
        charm_component=0,
        estimated_hedge_demand=0,
        positioning_confidence=0,
        label=label,
    )
    result = run_experiment("zero", [row], zero_move)
    assert result.name == "zero"
    assert result.metrics.samples == 1
