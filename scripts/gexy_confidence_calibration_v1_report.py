from __future__ import annotations

import argparse
import json

from packages.gexy.confidence_calibration_v1 import build_confidence_calibration_v1_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fit the frozen GEXY confidence-calibration v1 selection model and score independent sessions"
    )
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    args = parser.parse_args()

    report = build_confidence_calibration_v1_report(journal_path=args.journal)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
