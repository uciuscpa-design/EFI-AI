from datetime import datetime, timedelta, timezone

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.regime_evaluation import evaluate_by_regime
from packages.gexy.regimes import Regime


def row(i: int) -> ResearchRow:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc) + timedelta(minutes=i)
    move = float(i - 5)
    return ResearchRow(
        timestamp=ts, spot=6500 + move, spot_change=move, iv_change=0.001 * i,
        total_gex=100 + i, gamma_change=1, vanna_component=0.1 * i,
        charm_component=-0.05 * i, estimated_hedge_demand=0.2 * move,
        positioning_confidence=0.8, label=make_label(6500 + move, 6500 + move, 5),
    )


def test_evaluate_by_regime_groups_rows() -> None:
    rows = [row(i) for i in range(8)]
    regimes = [Regime("positive", 2, "above_flip", "normal", False) for _ in rows]
    results = evaluate_by_regime(rows, regimes)
    assert len(results) == 1
    assert results[0].samples == 8
