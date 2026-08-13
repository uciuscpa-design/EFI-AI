from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone

from packages.gexy.alpaca_provider import AlpacaSpxSnapshotProvider
from packages.gexy.live_pipeline import run_live_pipeline


def main() -> int:
    provider = AlpacaSpxSnapshotProvider()
    observation = provider(datetime.now(timezone.utc))
    result = run_live_pipeline(
        observation.feature_state,
        spot=observation.spot,
        horizon_minutes=30,
    )
    payload = {
        "timestamp": observation.timestamp.isoformat(),
        "spot": observation.spot,
        "prediction": asdict(result.prediction),
        "surface": asdict(result.surface_features),
        "quote_count": len(observation.quote_times),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
