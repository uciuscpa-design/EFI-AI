from __future__ import annotations

import argparse
import json

from packages.gexy.journal_horizon_report import build_journal_horizon_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Print GEXY live prediction journal and per-horizon metrics")
    parser.add_argument("--journal", default="data/gexy/live_predictions.jsonl")
    args = parser.parse_args()
    print(json.dumps(build_journal_horizon_report(args.journal), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
