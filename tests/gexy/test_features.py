from datetime import datetime, timezone

from packages.gexy.data import FeatureSnapshot, PriceSnapshot
from packages.gexy.features import build_feature_vector


def test_feature_vector_uses_snapshot_price() -> None:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    snapshot = FeatureSnapshot(
        timestamp=ts,
        spx=PriceSnapshot(ts, "SPX", 6500),
        es=None,
        options=(),
    )
    result = build_feature_vector(snapshot, [], positioning_confidence=0.25)
    assert result.spot == 6500
    assert result.total_gex == 0
    assert result.positioning_confidence == 0.25
