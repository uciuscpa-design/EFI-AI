from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from packages.gexy.h5_slope_invert_v1 import build_h5_slope_invert_v1_report
from packages.gexy.log_text import read_log_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the frozen GEXY-H5-SLOPE-INVERT-v1 hypothesis on independent sessions"
    )
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    parser.add_argument(
        "--log-glob",
        default="data/gexy/logs/session-*.log",
        help="glob containing collector logs with source-time surface features",
    )
    args = parser.parse_args()

    log_paths = sorted(Path().glob(args.log_glob))
    with TemporaryDirectory(prefix="gexy-h5-v1-") as temp_dir:
        normalized_paths: list[Path] = []
        for index, source in enumerate(log_paths):
            destination = Path(temp_dir) / f"{index:03d}-{source.name}"
            destination.write_text(read_log_text(source), encoding="utf-8")
            normalized_paths.append(destination)

        report = build_h5_slope_invert_v1_report(
            journal_path=args.journal,
            log_paths=normalized_paths,
        )

    report["log_paths"] = [str(path) for path in log_paths]
    report["log_encoding_normalized"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
