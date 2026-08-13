from datetime import datetime, timezone

from packages.gexy.live_pipeline import run_live_pipeline, surface_points_from_snapshot
from packages.gexy.market_adapter import MarketSnapshot, OptionSnapshot


def _snapshot() -> MarketSnapshot:
    expiry = datetime(2026, 8, 13, 20, 0, tzinfo=timezone.utc)
    options = (
        OptionSnapshot("7700", 7700, expiry, call_gamma=-40, put_gamma=-42),
        OptionSnapshot("7730", 7730, expiry, call_gamma=-50, put_gamma=-54),
        OptionSnapshot("7740", 7740, expiry, call_gamma=100, put_gamma=83),
        OptionSnapshot("7750", 7750, expiry, call_gamma=90, put_gamma=78),
        OptionSnapshot("7760", 7760, expiry, call_gamma=170, put_gamma=156),
    )
    return MarketSnapshot(
        timestamp=datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        spot=7749.2,
        iv=0.10,
        options=options,
    )


def test_surface_points_from_snapshot_aggregates_signed_gex() -> None:
    points = surface_points_from_snapshot(_snapshot())
    assert [point.strike for point in points] == [7700, 7730, 7740, 7750, 7760]
    assert points[1].signed_gex == -104
    assert points[-1].signed_gex == 326


def test_run_live_pipeline_emits_prediction() -> None:
    result = run_live_pipeline(_snapshot(), horizon_minutes=30)
    assert result.surface_features.positive_gamma_regime is True
    assert result.surface_features.flip_level is not None
    assert 7730 < result.surface_features.flip_level < 7740
    assert result.prediction.direction == "down"
    assert result.prediction.primary_target == 7740
    assert result.prediction.horizon_minutes == 30
    assert result.prediction.regime == "positive_gamma_mean_reversion"
