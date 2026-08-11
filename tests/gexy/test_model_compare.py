from datetime import datetime, timedelta, timezone

from packages.gexy.calibration import make_label
from packages.gexy.dataset import ResearchRow
from packages.gexy.model_compare import compare_models


def row(i: int) -> ResearchRow:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc) + timedelta(minutes=i)
    move = float((i % 7) - 3)
    return ResearchRow(
        timestamp=ts, spot=6500 + move, spot_change=move, iv_change=0.001 * i,
        total_gex=100 + i, gamma_change=move * 0.2, vanna_component=move * 0.1,
        charm_component=move * -0.05, estimated_hedge_demand=move * 0.3,
        positioning_confidence=0.8, label=make_label(6500 + move, 6500 + move + move, 5),
    )


def test_compare_models_returns_all_nested_variants() -> None:
    results = compare_models([row(i) for i in range(30)])
    assert [item.name for item in results] == ["gex", "gex_vanna", "gex_vanna_charm", "full"]
    assert all(item.test_metrics.samples == 6 for item in results)
