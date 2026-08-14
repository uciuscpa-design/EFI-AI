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


def run_loop(*, interval_seconds: int = 60, tolerance_seconds: int = 90) -> int:
    """Wait for the session, collect every interval, then stop after session close.

    Starting this process before the regular session is safe: skipped cycles are treated
    as a waiting state until at least one successful in-session collection has occurred.
    After collection has begun, the first outside-session observation ends the process.
    """
    collected_in_session = False
    while True:
        payload = run_cycle(tolerance_seconds=tolerance_seconds)
        print(json.dumps(payload, sort_keys=True), flush=True)

        status = payload.get("status")
        if status == "error":
            return 2
        if status == "ok":
            collected_in_session = True
            time.sleep(interval_seconds)
            continue
        if status == "skipped" and collected_in_session:
            return 0

        # Before the first successful session cycle, remain armed and wait for open.
        time.sleep(interval_seconds)


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

    return run_loop(
        interval_seconds=args.interval_seconds,
        tolerance_seconds=args.tolerance_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
