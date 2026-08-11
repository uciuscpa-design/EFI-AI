from datetime import datetime, timedelta, timezone

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.evaluation import evaluate


def make_row(i: int) -> ResearchRow:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc) + timedelta(minutes=i)
    move = float(i - 5)
    return ResearchRow(
        timestamp=ts,
        spot=6500 + move,
        spot_change=move,
        iv_change=0.001 * i,
        total_gex=100 + i,
        gamma_change=1,
        vanna_component=0.1 * i,
        charm_component=-0.05 * i,
        estimated_hedge_demand=move,
        positioning_confidence=0.8,
        label=make_label(6500 + move, 6500 + move + move, 5),
    )


def test_evaluate_uses_chronological_test_set() -> None:
    result = evaluate([make_row(i) for i in range(20)])
    assert result.train_samples == 12
    assert result.validation_samples == 4
    assert result.test_samples == 4
