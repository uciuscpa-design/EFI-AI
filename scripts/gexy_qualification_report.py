from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from packages.gexy.prediction_journal import load_entries
from packages.gexy.qualification import qualify_horizons


def _load_snapshot_sessions(root: Path) -> dict[str, list]:
    sessions: dict[str, list] = {}
    if not root.exists():
        return sessions
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        journal = directory / "shadow_predictions.jsonl"
        if not journal.exists():
            continue
        rows = load_entries(journal)
        if rows:
            sessions[directory.name] = rows
    return sessions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate GEXY fine horizons across frozen session snapshots with conservative abstention gates"
    )
    parser.add_argument("--snapshots-root", default="projects/gexy/snapshots")
    parser.add_argument("--target-accuracy", type=float, default=0.95)
    parser.add_argument("--minimum-resolved", type=int, default=100)
    parser.add_argument("--minimum-sessions", type=int, default=3)
    parser.add_argument("--minimum-lift", type=float, default=0.05)
    parser.add_argument("--minimum-positive-session-fraction", type=float, default=2.0 / 3.0)
    parser.add_argument("--minimum-resolution-coverage", type=float, default=0.90)
    args = parser.parse_args()

    sessions = _load_snapshot_sessions(Path(args.snapshots_root))
    report = qualify_horizons(
        sessions,
        target_directional_accuracy=args.target_accuracy,
        minimum_resolved=args.minimum_resolved,
        minimum_sessions=args.minimum_sessions,
        minimum_lift_vs_baseline=args.minimum_lift,
        minimum_positive_lift_session_fraction=args.minimum_positive_session_fraction,
        minimum_resolution_coverage=args.minimum_resolution_coverage,
    )

    payload = {
        "status": report.status,
        "automatic_promotion": report.automatic_promotion,
        "sessions": list(report.session_dates),
        "session_count": len(report.session_dates),
        "qualified_horizons_minutes": list(report.qualified_horizons_minutes),
        "shortest_qualified_horizon_minutes": report.shortest_qualified_horizon_minutes,
        "gates": {
            "target_directional_accuracy": args.target_accuracy,
            "minimum_resolved": args.minimum_resolved,
            "minimum_sessions": args.minimum_sessions,
            "minimum_lift_vs_baseline": args.minimum_lift,
            "minimum_positive_lift_session_fraction": args.minimum_positive_session_fraction,
            "minimum_resolution_coverage": args.minimum_resolution_coverage,
        },
        "by_horizon": {
            str(metric.horizon_minutes): asdict(metric)
            for metric in report.horizons
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
