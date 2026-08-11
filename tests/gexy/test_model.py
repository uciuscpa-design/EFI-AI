from datetime import datetime, timezone

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.model import fit_ridge, predict


def row(move: float, hedge: float) -> ResearchRow:
    return ResearchRow(
        timestamp=datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc),
        spot=6500,
        spot_change=move,
        iv_change=0,
        total_gex=100,
        gamma_change=0,
        vanna_component=0,
        charm_component=0,
        estimated_hedge_demand=hedge,
        positioning_confidence=0.8,
        label=make_label(6500, 6500 + move, 5),
    )


def test_ridge_fit_predict_is_finite() -> None:
    model = fit_ridge([row(-3, -2), row(0, 0), row(4, 3), row(7, 5)])
    prediction = predict(model, row(2, 1))
    assert 0 <= prediction.up_probability <= 1
    assert prediction.move_points == prediction.move_points
