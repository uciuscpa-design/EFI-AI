from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from packages.gexy.off_exchange_sources import (
    normalize_alpaca_sip_trades,
    normalize_databento_equity_trades,
    normalize_massive_stock_trades,
)


def _read_json_records(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return pd.DataFrame()
    if text.startswith("["):
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("JSON capture must contain a list of messages")
        return pd.DataFrame(payload)

    records: list[object] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
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
            "Normalize already-captured Massive, Alpaca SIP, or Databento equity trades into the "
            "GEXY off-exchange/TRF contract. This command performs local file processing only and "
            "makes no market-data requests."
        )
    )
    parser.add_argument("--provider", required=True, choices=("massive", "alpaca_sip", "databento"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--alpaca-off-exchange-codes",
        default="",
        help=(
            "comma-separated Alpaca SIP exchange-code allow-list; required for provider=alpaca_sip "
            "and intentionally has no default"
        ),
    )
    parser.add_argument(
        "--databento-dataset",
        default="",
        help="Databento dataset name such as XNAS.BASIC; required for provider=databento",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"input file was not found: {args.input}")

    try:
        if args.provider == "massive":
            raw = _read_json_records(args.input)
            normalized = normalize_massive_stock_trades(raw)
        elif args.provider == "alpaca_sip":
            codes = _parse_codes(args.alpaca_off_exchange_codes)
            if not codes:
                raise ValueError(
                    "--alpaca-off-exchange-codes is required; verify Alpaca exchange metadata first"
                )
            raw = _read_json_records(args.input)
            normalized = normalize_alpaca_sip_trades(raw, off_exchange_codes=codes)
        else:
            dataset = args.databento_dataset.strip().upper()
            if not dataset:
                raise ValueError("--databento-dataset is required for provider=databento")
            raw = pd.read_csv(args.input)
            normalized = normalize_databento_equity_trades(raw, dataset=dataset)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False)

    print("GEXY OFF-EXCHANGE SOURCE CAPTURE NORMALIZATION")
    print(f"PROVIDER: {args.provider}")
    print(f"INPUT: {args.input}")
    print(f"OFF-EXCHANGE/TRF RECORDS: {len(normalized)}")
    if not normalized.empty:
        print(f"SYMBOLS: {normalized['symbol'].nunique()}")
        print(f"FIRST AVAILABLE_AT: {normalized['available_at'].min()}")
        print(f"LAST AVAILABLE_AT: {normalized['available_at'].max()}")
        print("REPORTING VENUES:")
        print(normalized["reporting_venue"].value_counts().to_string())
    print(f"OUTPUT: {args.output}")
    print("CAUSALITY: available_at is provider-specific dissemination/capture time, not inferred execution intent.")
    print("NO PAID DATA REQUESTS: this command reads only the local input capture.")


if __name__ == "__main__":
    main()
