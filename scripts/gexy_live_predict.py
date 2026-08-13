from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from packages.gexy.alpaca_live import predict_from_alpaca


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one live GEXY SPX prediction from Alpaca data")
    parser.add_argument("--horizon", type=int, default=30, help="forecast horizon in minutes")
    args = parser.parse_args()

    result = predict_from_alpaca(horizon_minutes=args.horizon)
    payload = {
        "timestamp": result.timestamp.isoformat(),
        "spot": result.spot,
        "prediction": asdict(result.pipeline.prediction),
        "surface": asdict(result.pipeline.surface_features),
        "quote_count": len(result.quote_times),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
