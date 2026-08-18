from __future__ import annotations

import argparse
from pathlib import Path

from packages.gexy.finra_short_volume import (
    normalize_finra_daily_short_volume,
    read_finra_daily_short_volume,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize an already-downloaded FINRA Daily Short Sale Volume file into causal GEXY "
            "context. This command performs local file processing only and makes no network requests."
        )
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--facility", required=True)
    parser.add_argument(
        "--available-at",
        required=True,
        help="exact timezone-aware timestamp when this file became observable to GEXY",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"input file was not found: {args.input}")

    try:
        normalized = normalize_finra_daily_short_volume(
            read_finra_daily_short_volume(args.input),
            facility=args.facility,
            available_at=args.available_at,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(args.output, index=False)

    print("GEXY FINRA DAILY SHORT-VOLUME CONTEXT")
    print(f"INPUT: {args.input}")
    print(f"FACILITY: {args.facility}")
    print(f"ROWS: {len(normalized)}")
    print(f"AVAILABLE_AT: {normalized['available_at'].iloc[0] if len(normalized) else args.available_at}")
    print(f"OUTPUT: {args.output}")
    print("INTERPRETATION: short-sale volume context only; not short interest or net positioning.")
    print("NO NETWORK REQUESTS: this command reads only the local FINRA file.")


if __name__ == "__main__":
    main()
