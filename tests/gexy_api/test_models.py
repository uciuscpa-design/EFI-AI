from datetime import datetime, timezone

import pytest

from apps.gexy_api.models import ModelBundle, ModelRegistry


def test_registry_rejects_missing_models() -> None:
    registry = ModelRegistry()
    with pytest.raises(ValueError):
        registry.load(ModelBundle("v1", datetime.now(timezone.utc), {}))
