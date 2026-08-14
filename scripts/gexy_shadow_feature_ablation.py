from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.gexy.shadow_feature_ablation import build_shadow_feature_ablation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run advisory-only feature ablation on resolved GEXY shadow forecasts"
    )
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    parser.add_argument(
        "--log-glob",
        default="data/gexy/logs/session-*.log",
        help="glob containing session collector logs with live surface features",
    )
    args = parser.parse_args()

    log_paths = sorted(Path().glob(args.log_glob))
    report = build_shadow_feature_ablation(
        journal_path=args.journal,
        log_paths=log_paths,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
