from __future__ import annotations

import argparse
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

from packages.gexy.session_cadence import summarize_cadence

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_SCRIPT = ROOT / "scripts" / "gexy_snapshot_session.py"


def _load_snapshot_helpers():
    spec = importlib.util.spec_from_file_location("gexy_snapshot_session_helpers", SNAPSHOT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load GEXY snapshot helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Report actual GEXY collector observation cadence from a frozen session")
    parser.add_argument("--session-date", required=True, help="session date in YYYY-MM-DD")
    parser.add_argument("--snapshots-root", default="projects/gexy/snapshots")
    parser.add_argument("--target-interval-seconds", type=float, default=60.0)
    parser.add_argument("--largest-gaps", type=int, default=10)
    args = parser.parse_args()

    log_path = Path(args.snapshots_root) / args.session_date / f"session-{args.session_date}.log"
    if not log_path.exists():
        print(json.dumps({"status": "error", "error": f"snapshot log not found: {log_path}"}, indent=2))
        return 2

    helpers = _load_snapshot_helpers()
    observed_times = helpers._observed_times_from_log(log_path)
    report = summarize_cadence(
        observed_times,
        target_interval_seconds=args.target_interval_seconds,
        largest_gap_count=args.largest_gaps,
    )
    payload = {
        "status": "ok",
        "session_date": args.session_date,
        "log": str(log_path.as_posix()),
        **asdict(report),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
