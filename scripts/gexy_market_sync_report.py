from __future__ import annotations

import argparse
import json

from packages.gexy.market_sync_journal import build_sync_coverage_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report GEXY SPX/ES point-in-time synchronization coverage and integrity"
    )
    parser.add_argument(
        "--journal",
        default="data/gexy/spx_es_sync.jsonl",
        help="append-only SPX/ES synchronization journal",
    )
    args = parser.parse_args()

    report = build_sync_coverage_report(args.journal)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
