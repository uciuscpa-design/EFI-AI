from datetime import datetime, timezone

import pytest

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.model_runner import run_chronological


def make_rows(n: int, start: float = 6500) -> list[ResearchRow]:
    rows = []
    for i in range(n):
        spot = start + i
        rows.append(ResearchRow(
            timestamp=datetime(2026, 8, 10, 13, i, tzinfo=timezone.utc),
            spot=spot,
            spot_change=1.0,
            iv_change=0.001,
            total_gex=10 + i,
            gamma_change=0.1,
            vanna_component=0.2,
            charm_component=0.3,
            estimated_hedge_demand=0.4,
            positioning_confidence=0.8,
            label=make_label(spot, spot, 1),
        ))
    return rows


def test_runner_fits_only_training() -> None:
    report = run_chronological(make_rows(8), make_rows(4, 6600), make_rows(4, 6700))
    assert report.train.samples == 8
    assert report.validation.samples == 4
    assert report.test.samples == 4


def test_runner_requires_training_data() -> None:
    with pytest.raises(ValueError):
        run_chronological([], make_rows(2), make_rows(2))
