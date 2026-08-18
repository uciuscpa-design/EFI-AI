from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from packages.gexy.off_exchange_live_normalization import (
    normalize_alpaca_sip_live_capture,
    normalize_massive_live_capture,
)


def _read_json_records(path: Path) -> pd.DataFrame:
    records: list[object] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, list):
            records.extend(payload)
        elif isinstance(payload, dict):
            records.append(payload)
        else:
            raise ValueError(f"JSONL line {line_number} is not an object or list")
    return pd.DataFrame(records)


def _parse_codes(value: str) -> set[str]:
    return {item.strip().upper() for item in value.split(",") if item.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a raw GEXY-stamped Massive or Alpaca SIP WebSocket capture. The resulting "
            "available_at is never earlier than gexy_received_at. No network request is made."
        )
    )
    parser.add_argument("--provider", required=True, choices=("massive", "alpaca_sip"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--alpaca-off-exchange-codes",
        default="",
        help="explicit verified Alpaca SIP off-exchange exchange-code allow-list",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"input file was not found: {args.input}")

    try:
        raw = _read_json_records(args.input)
        if args.provider == "massive":
            normalized = normalize_massive_live_capture(raw)
        else:
            codes = _parse_codes(args.alpaca_off_exchange_codes)
            if not codes:
                raise ValueError("--alpaca-off-exchange-codes is required for Alpaca SIP")
            normalized = normalize_alpaca_sip_live_capture(raw, off_exchange_codes=codes)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False)

    print("GEXY LIVE OFF-EXCHANGE CAPTURE NORMALIZATION")
    print(f"PROVIDER: {args.provider}")
    print(f"INPUT: {args.input}")
    print(f"TRF/OFF-EXCHANGE RECORDS: {len(normalized)}")
    print(f"OUTPUT: {args.output}")
    print("CAUSALITY: available_at=max(provider-derived time, gexy_received_at)")
    print("NO NETWORK REQUESTS: this command reads only the local raw capture.")


if __name__ == "__main__":
    main()
