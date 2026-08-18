from __future__ import annotations

import argparse
import sys
from typing import Any

from packages.data.alpaca_options import (
    AlpacaOptionsClient,
    AlpacaOptionsError,
    option_chain_snapshot_count,
)


def _sample_contract_symbols(payload: dict[str, Any], limit: int = 5) -> list[str]:
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, dict):
        return []
    return list(snapshots.keys())[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GEXY smoke test: validate Alpaca auth and fetch an option-chain sample."
    )
    parser.add_argument(
        "--symbol",
        default="SPX",
        help="Underlying symbol to request (default: SPX).",
    )
    parser.add_argument(
        "--feed",
        choices=("indicative", "opra"),
        default=None,
        help="Alpaca options feed. Defaults to APCA_OPTIONS_FEED or indicative.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum option snapshots to request (1-1000, default: 25).",
    )
    args = parser.parse_args()

    try:
        with AlpacaOptionsClient() as client:
            client.check_authentication()
            payload = client.fetch_option_chain(
                args.symbol,
                limit=args.limit,
                feed=args.feed,
            )
    except (AlpacaOptionsError, ValueError) as exc:
        print(f"GEXY smoke test failed: {exc}", file=sys.stderr)
        return 1

    selected_feed = args.feed or "configured default"
    count = option_chain_snapshot_count(payload)
    sample_symbols = _sample_contract_symbols(payload)

    print("Alpaca authentication: OK")
    print(f"Underlying: {args.symbol.strip().upper()}")
    print(f"Feed: {selected_feed}")
    print(f"Snapshots returned: {count}")
    if payload.get("next_page_token"):
        print("More snapshots available: yes")
    if sample_symbols:
        print("Sample contracts:")
        for symbol in sample_symbols:
            print(f"  {symbol}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
