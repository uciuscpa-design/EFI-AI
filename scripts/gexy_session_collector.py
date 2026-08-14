from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from packages.gexy.alpaca_calendar import is_alpaca_market_session

ROOT = Path(__file__).resolve().parents[1]


def _run_script(script_name: str, *args: str) -> dict[str, object]:
    command = [sys.executable, str(ROOT / "scripts" / script_name), *args]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = completed.stdout.strip()
    payload: dict[str, object]
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        payload = {"stdout": stdout}
    payload["exit_code"] = completed.returncode
    if completed.stderr.strip():
        payload["stderr"] = completed.stderr.strip()
    return payload


def run_cycle(*, tolerance_seconds: int = 90) -> dict[str, object]:
    observed_at = datetime.now(timezone.utc)
    if not is_alpaca_market_session(observed_at):
        return {
            "status": "skipped",
            "reason": "outside_alpaca_market_session",
            "observed_at": observed_at.isoformat(),
        }

    resolution = _run_script(
        "gexy_resolve_due.py",
        "--tolerance-seconds",
        str(tolerance_seconds),
    )
    if int(resolution.get("exit_code", 1)) != 0:
        return {
            "status": "error",
            "stage": "resolve_due",
            "observed_at": observed_at.isoformat(),
            "resolution": resolution,
        }

    prediction = _run_script("gexy_live_predict.py", "--horizon", "30")
    if int(prediction.get("exit_code", 1)) != 0:
        return {
            "status": "error",
            "stage": "live_predict",
            "observed_at": observed_at.isoformat(),
            "resolution": resolution,
            "prediction": prediction,
        }

    return {
        "status": "ok",
        "observed_at": observed_at.isoformat(),
        "resolution": resolution,
        "prediction": prediction,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect and resolve GEXY forecasts once per minute during Alpaca market sessions"
    )
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--tolerance-seconds", type=int, default=90)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.interval_seconds < 30:
        parser.error("--interval-seconds must be at least 30")
    if args.tolerance_seconds < 0:
        parser.error("--tolerance-seconds must be non-negative")

    if args.once:
        payload = run_cycle(tolerance_seconds=args.tolerance_seconds)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") != "error" else 2

    while True:
        payload = run_cycle(tolerance_seconds=args.tolerance_seconds)
        print(json.dumps(payload, sort_keys=True), flush=True)
        if payload.get("status") == "skipped":
            return 0
        if payload.get("status") == "error":
            return 2
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
