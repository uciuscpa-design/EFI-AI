from __future__ import annotations

import argparse
import json

from packages.gexy.gax_shadow_version_sweep import build_consolidated_shadow_v2_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Print read-only GEXY GAX shadow-v2 evaluation and readiness metrics")
    parser.add_argument("--journal", default="data/gexy/live_predictions.jsonl")
    parser.add_argument("--gax-shadow-journal", default="data/gexy/gax_shadow.jsonl")
    args = parser.parse_args()
    report = build_consolidated_shadow_v2_report(args.journal, args.gax_shadow_journal)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
