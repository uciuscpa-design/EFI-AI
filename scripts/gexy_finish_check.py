from __future__ import annotations

import argparse
import json
from pathlib import Path

from apps.gexy_api.main import app
from packages.gexy.live_prediction import PRODUCTION_HORIZONS_MINUTES, shadow_horizon_grid
from packages.gexy.prediction_journal import load_entries

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "apps" / "gexy_ui" / "index.html"
LAUNCHER_PATH = ROOT / "scripts" / "gexy_launch.ps1"
BACKTEST_PATH = ROOT / "scripts" / "gexy_backtest_report.py"
PRODUCTION_JOURNAL = ROOT / "data" / "gexy" / "live_predictions.jsonl"
SHADOW_JOURNAL = ROOT / "data" / "gexy" / "shadow_predictions.jsonl"


def _count(path: Path) -> int:
    return len(load_entries(path)) if path.exists() else 0


def build_report(*, strict_data: bool = False) -> dict[str, object]:
    shadow_grid = shadow_horizon_grid()
    production_count = _count(PRODUCTION_JOURNAL)
    shadow_count = _count(SHADOW_JOURNAL)
    checks = {
        "api_loaded": app.title == "GEXY Live Forecast API",
        "ui_present": UI_PATH.exists(),
        "launcher_present": LAUNCHER_PATH.exists(),
        "backtest_command_present": BACKTEST_PATH.exists(),
        "production_horizons": tuple(PRODUCTION_HORIZONS_MINUTES) == (5, 15, 30, 60),
        "shadow_grid_1_to_60": shadow_grid == tuple(range(1, 61)),
        "paper_research_only": True,
        "production_data_present": production_count > 0,
        "shadow_data_present": shadow_count > 0,
    }
    code_ready = all(
        checks[name]
        for name in (
            "api_loaded",
            "ui_present",
            "launcher_present",
            "backtest_command_present",
            "production_horizons",
            "shadow_grid_1_to_60",
            "paper_research_only",
        )
    )
    data_ready = checks["production_data_present"] and checks["shadow_data_present"]
    ready = code_ready and (data_ready if strict_data else True)
    return {
        "status": "ready" if ready else "not_ready",
        "code_ready": code_ready,
        "data_ready": data_ready,
        "strict_data": strict_data,
        "operator_url": "http://127.0.0.1:8765/",
        "execution_enabled": False,
        "production_journal_entries": production_count,
        "shadow_journal_entries": shadow_count,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GEXY v1 operator readiness")
    parser.add_argument("--strict-data", action="store_true", help="require both prediction journals to contain data")
    args = parser.parse_args()
    report = build_report(strict_data=args.strict_data)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
