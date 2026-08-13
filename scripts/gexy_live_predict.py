from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from urllib.error import HTTPError

from packages.gexy.alpaca_live import predict_from_alpaca


def _credential_meta() -> dict[str, object]:
    key = (os.getenv("APCA_API_KEY_ID") or "").strip()
    prefix = key[:2].upper() if len(key) >= 2 else ""
    return {
        "key_present": bool(key),
        "key_prefix": prefix,
        "key_length": len(key),
    }


def _paper_key_shape_is_plausible() -> bool:
    meta = _credential_meta()
    return bool(meta["key_present"]) and meta["key_prefix"] == "PK" and int(meta["key_length"]) >= 16


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one live GEXY SPX prediction from Alpaca data")
    parser.add_argument("--horizon", type=int, default=30, help="forecast horizon in minutes")
    args = parser.parse_args()

    if not _paper_key_shape_is_plausible():
        payload = {
            "status": "error",
            "error": "invalid_paper_credential_shape",
            "credential": _credential_meta(),
            "next_action": "Replace APCA_API_KEY_ID/APCA_API_SECRET_KEY with the Paper Trading API key pair, then rerun live-predict.",
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 2

    try:
        result = predict_from_alpaca(horizon_minutes=args.horizon)
    except HTTPError as exc:
        payload = {
            "status": "error",
            "error": "alpaca_authentication_failed" if exc.code == 401 else "alpaca_http_error",
            "http_status": exc.code,
            "credential": _credential_meta(),
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
