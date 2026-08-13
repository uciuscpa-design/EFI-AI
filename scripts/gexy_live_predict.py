from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from urllib.error import HTTPError

from packages.gexy.alpaca_live import predict_from_alpaca


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one live GEXY SPX prediction from Alpaca data")
    parser.add_argument("--horizon", type=int, default=30, help="forecast horizon in minutes")
    args = parser.parse_args()

    try:
        result = predict_from_alpaca(horizon_minutes=args.horizon)
    except HTTPError as exc:
        key = (os.getenv("APCA_API_KEY_ID") or "").strip()
        prefix = key[:2] if len(key) >= 2 else ""
        payload = {
            "status": "error",
            "error": "alpaca_authentication_failed" if exc.code == 401 else "alpaca_http_error",
            "http_status": exc.code,
            "credential": {
                "key_present": bool(key),
                "key_prefix": prefix,
                "key_length": len(key),
            },
            "next_action": (
                "Replace APCA_API_KEY_ID/APCA_API_SECRET_KEY with the Paper Trading API key pair, then rerun live-predict."
                if exc.code == 401
                else "Check Alpaca service access and rerun live-predict."
            ),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    payload = {
        "status": "ok",
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
