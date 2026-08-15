from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.gexy.log_text import read_log_text
from packages.gexy.shadow_horizon_holdout import build_horizon_holdout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run chronological horizon holdout checks for advisory GEXY shadow rules"
    )
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    parser.add_argument("--log-glob", default="data/gexy/logs/session-*.log")
    parser.add_argument("--train-fraction", type=float, default=0.70)
    args = parser.parse_args()

    log_paths = sorted(Path().glob(args.log_glob))
    with TemporaryDirectory(prefix="gexy-horizon-holdout-") as temp_dir:
        normalized_paths: list[Path] = []
        for index, source in enumerate(log_paths):
            destination = Path(temp_dir) / f"{index:03d}-{source.name}"
            destination.write_text(read_log_text(source), encoding="utf-8")
            normalized_paths.append(destination)
        report = build_horizon_holdout(
            journal_path=args.journal,
            log_paths=normalized_paths,
            train_fraction=args.train_fraction,
        )

    report["log_paths"] = [str(path) for path in log_paths]
    report["log_encoding_normalized"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
