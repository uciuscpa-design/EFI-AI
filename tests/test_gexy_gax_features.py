from datetime import datetime, timezone

import pytest

from packages.gexy.gax_features import build_gax_features
from packages.gexy.gax_shadow_journal import (
    append_gax_shadow,
    load_gax_shadows,
    make_gax_shadow_record,
    summarize_gax_shadow,
)
from packages.gexy.live_prediction import LivePrediction
from packages.gexy.prediction_journal import make_entry, resolve_entry
from packages.gexy.surface_features import GEXSurfacePoint, build_surface_features


def test_gax_proxy_tracks_local_gex_slope() -> None:
    points = (
        GEXSurfacePoint(7730, -100.0),
        GEXSurfacePoint(7740, 0.0),
        GEXSurfacePoint(7750, 100.0),
    )
    features = build_gax_features(points, spot=7742.0)
    assert features.local_gax > 0
    assert features.acceleration_bias == "up"
    assert features.local_gax_curvature == 0.0
    assert features.source == "gex_spatial_derivative_proxy_v1"


def test_gax_proxy_detects_curvature() -> None:
    points = (
        GEXSurfacePoint(7730, -100.0),
        GEXSurfacePoint(7740, -50.0),
        GEXSurfacePoint(7750, 100.0),
    )
    features = build_gax_features(points, spot=7740.0)
    assert features.local_gax > 0
    assert features.local_gax_curvature > 0
    assert features.magnitude == abs(features.local_gax)


def test_gax_proxy_neutral_for_flat_curve() -> None:
    points = (
        GEXSurfacePoint(7730, 25.0),
        GEXSurfacePoint(7740, 25.0),
        GEXSurfacePoint(7750, 25.0),
    )
    features = build_gax_features(points, spot=7740.0)
    assert features.local_gax == 0.0
    assert features.local_gax_curvature == 0.0
    assert features.acceleration_bias == "neutral"


def test_gax_v1_matches_legacy_hedge_acceleration_without_double_counting() -> None:
    points = (
        GEXSurfacePoint(7730, -104.0),
        GEXSurfacePoint(7740, 183.0),
        GEXSurfacePoint(7750, 168.0),
        GEXSurfacePoint(7760, 326.0),
    )
    spot = 7749.2
    gax = build_gax_features(points, spot=spot)
    gex = build_surface_features(points, spot=spot)
    assert gax.local_gax == pytest.approx(gex.hedge_acceleration)


def test_gax_shadow_journal_round_trip_and_scores_resolved_outcome(tmp_path) -> None:
    points = (
        GEXSurfacePoint(7730, -100.0),
        GEXSurfacePoint(7740, 0.0),
        GEXSurfacePoint(7750, 100.0),
    )
    gax = build_gax_features(points, spot=7742.0)
    prediction = LivePrediction(
        direction="up",
        expected_move_points=3.0,
        primary_target=7750.0,
        invalidation_level=7735.0,
        confidence=0.6,
        horizon_minutes=5,
        regime="positive_gamma_mean_reversion",
    )
    created = datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)
    entry = make_entry(created_at=created, spot=7742.0, prediction=prediction)
    shadow = make_gax_shadow_record(
        prediction_id=entry.prediction_id,
        created_at=created,
        horizon_minutes=5,
        model_version=entry.model_version,
        features=gax,
    )
    path = tmp_path / "gax_shadow.jsonl"
    append_gax_shadow(path, shadow)
    loaded = load_gax_shadows(path)
    assert loaded == [shadow]

    resolved = resolve_entry(entry, resolved_at=entry.due_at, realized_spot=7745.0)
    metrics = summarize_gax_shadow([resolved], loaded)
    assert metrics.resolved == 1
    assert metrics.bias_alignment_accuracy == 1.0
    assert metrics.mean_magnitude == pytest.approx(gax.magnitude)
    assert metrics.mean_absolute_curvature == pytest.approx(abs(gax.local_gax_curvature))
