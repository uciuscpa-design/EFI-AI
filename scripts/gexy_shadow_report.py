from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from packages.gexy.horizon_metrics import summarize_by_horizon
from packages.gexy.prediction_journal import load_entries


def build_shadow_report(path: str | Path) -> dict[str, object]:
    entries = load_entries(path)
    metrics = summarize_by_horizon(entries)
    qualified = [m for m in metrics if m.qualified_for_promotion]
    return {
        "journal": str(path),
        "model_versions": sorted({entry.model_version for entry in entries}),
        "total_entries": len(entries),
        "resolved_entries": sum(1 for entry in entries if entry.resolved),
        "shortest_qualified_horizon_minutes": (
            min(m.horizon_minutes for m in qualified) if qualified else None
        ),
        "qualified_horizons_minutes": [m.horizon_minutes for m in qualified],
        "by_horizon": {
            str(m.horizon_minutes): asdict(m)
            for m in metrics
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report GEXY fine-shadow horizon promotion metrics")
    parser.add_argument("--journal", default="data/gexy/shadow_predictions.jsonl")
    args = parser.parse_args()
    print(json.dumps(build_shadow_report(args.journal), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
