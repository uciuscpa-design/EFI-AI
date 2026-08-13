from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from urllib.error import HTTPError

from packages.gexy.alpaca_live import predict_from_alpaca
from packages.gexy.gax_shadow_journal import append_gax_shadow, make_gax_shadow_record
from packages.gexy.prediction_journal import append_entry, make_entry


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
    parser.add_argument("--horizon", type=int, default=30, help="primary forecast horizon in minutes")
    parser.add_argument(
        "--journal",
        default="data/gexy/live_predictions.jsonl",
        help="append-only JSONL path for successful predictions",
    )
    parser.add_argument(
        "--gax-shadow-journal",
        default="data/gexy/gax_shadow.jsonl",
        help="append-only JSONL path for experimental GAX shadow observations",
    )
    parser.add_argument("--no-journal", action="store_true", help="do not persist predictions or GAX shadow records")
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

    forecasts = result.pipeline.multi_horizon.predictions
    journal_path: str | None = None
    gax_shadow_path: str | None = None
    if not args.no_journal:
        path = Path(args.journal)
        shadow_path = Path(args.gax_shadow_journal)
        for prediction in forecasts:
            entry = make_entry(
                created_at=result.timestamp,
                spot=result.spot,
                prediction=prediction,
            )
            append_entry(path, entry)
            append_gax_shadow(
                shadow_path,
                make_gax_shadow_record(
                    prediction_id=entry.prediction_id,
                    created_at=result.timestamp,
                    horizon_minutes=prediction.horizon_minutes,
                    model_version=entry.model_version,
                    features=result.pipeline.gax_features,
                ),
            )
        journal_path = str(path)
        gax_shadow_path = str(shadow_path)

    payload = {
        "status": "ok",
        "timestamp": result.timestamp.isoformat(),
        "spot": result.spot,
        "prediction": asdict(result.pipeline.prediction),
        "predictions_by_horizon": {
            str(prediction.horizon_minutes): asdict(prediction)
            for prediction in forecasts
        },
        "surface": asdict(result.pipeline.surface_features),
        "gax_shadow": asdict(result.pipeline.gax_features),
        "quote_count": len(result.quote_times),
        "journal_path": journal_path,
        "gax_shadow_journal_path": gax_shadow_path,
        "journaled_forecasts": 0 if args.no_journal else len(forecasts),
        "journaled_gax_shadows": 0 if args.no_journal else len(forecasts),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
