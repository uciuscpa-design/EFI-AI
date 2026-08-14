from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from packages.gexy.alpaca_calendar import AlpacaMarketSession, alpaca_market_session_window

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


def _session_metadata(window: AlpacaMarketSession | None) -> dict[str, object]:
    return {
        "market_session_date": window.session_date if window else None,
        "market_session_open_at": window.open_at.isoformat() if window else None,
        "market_session_close_at": window.close_at.isoformat() if window else None,
    }


def _finish_cycle(
    payload: dict[str, object],
    *,
    cycle_started_at: datetime,
    cycle_started_monotonic: float,
) -> dict[str, object]:
    cycle_finished_at = datetime.now(timezone.utc)
    enriched = dict(payload)
    enriched["cycle_started_at"] = cycle_started_at.isoformat()
    enriched["cycle_finished_at"] = cycle_finished_at.isoformat()
    enriched["cycle_duration_seconds"] = max(0.0, time.monotonic() - cycle_started_monotonic)
    return enriched


def run_cycle(*, tolerance_seconds: int = 90) -> dict[str, object]:
    cycle_started_at = datetime.now(timezone.utc)
    cycle_started_monotonic = time.monotonic()
    observed_at = cycle_started_at
    try:
        session_window = alpaca_market_session_window(observed_at)
    except Exception as exc:
        return _finish_cycle(
            {
                "status": "error",
                "stage": "market_session",
                "reason": "calendar_unavailable",
                "observed_at": observed_at.isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                **_session_metadata(None),
            },
            cycle_started_at=cycle_started_at,
            cycle_started_monotonic=cycle_started_monotonic,
        )

    session_meta = _session_metadata(session_window)
    if session_window is None or not session_window.contains(observed_at):
        return _finish_cycle(
            {
                "status": "skipped",
                "reason": "outside_alpaca_market_session",
                "observed_at": observed_at.isoformat(),
                **session_meta,
            },
            cycle_started_at=cycle_started_at,
            cycle_started_monotonic=cycle_started_monotonic,
        )

    resolution = _run_script(
        "gexy_resolve_due.py",
        "--tolerance-seconds",
        str(tolerance_seconds),
    )
    if int(resolution.get("exit_code", 1)) != 0:
        return _finish_cycle(
            {
                "status": "error",
                "stage": "resolve_due",
                "observed_at": observed_at.isoformat(),
                "resolution": resolution,
                **session_meta,
            },
            cycle_started_at=cycle_started_at,
            cycle_started_monotonic=cycle_started_monotonic,
        )

    prediction = _run_script("gexy_live_predict.py", "--horizon", "30")
    if int(prediction.get("exit_code", 1)) != 0:
        return _finish_cycle(
            {
                "status": "error",
                "stage": "live_predict",
                "observed_at": observed_at.isoformat(),
                "resolution": resolution,
                "prediction": prediction,
                **session_meta,
            },
            cycle_started_at=cycle_started_at,
            cycle_started_monotonic=cycle_started_monotonic,
        )

    return _finish_cycle(
        {
            "status": "ok",
            "observed_at": observed_at.isoformat(),
            "resolution": resolution,
            "prediction": prediction,
            **session_meta,
        },
        cycle_started_at=cycle_started_at,
        cycle_started_monotonic=cycle_started_monotonic,
    )


def _schedule_after_cycle(
    *,
    scheduled_tick: float,
    cycle_started: float,
    interval_seconds: int,
) -> tuple[dict[str, object], float]:
    """Return scheduler diagnostics and the next future wall-clock tick.

    Ticks remain anchored to the original monotonic schedule. Slow cycles do not
    add another full interval after completion, and missed ticks are skipped rather
    than replayed in a burst.
    """
    finished = time.monotonic()
    cycle_elapsed = max(0.0, finished - cycle_started)
    next_tick = scheduled_tick + interval_seconds
    missed_intervals = 0
    while next_tick <= finished:
        next_tick += interval_seconds
        missed_intervals += 1
    sleep_seconds = max(0.0, next_tick - finished)
    scheduler = {
        "target_interval_seconds": interval_seconds,
        "start_lag_seconds": max(0.0, cycle_started - scheduled_tick),
        "cycle_elapsed_seconds": cycle_elapsed,
        "overrun_seconds": max(0.0, cycle_elapsed - interval_seconds),
        "missed_intervals": missed_intervals,
        "sleep_seconds": sleep_seconds,
    }
    return scheduler, next_tick


def run_loop(*, interval_seconds: int = 60, tolerance_seconds: int = 90) -> int:
    """Wait for the session and collect on anchored wall-clock target ticks.

    Starting this process before the regular session is safe. Calendar/network/API
    errors are logged and retried. After each cycle, the next start stays anchored
    to the target interval instead of sleeping a full interval after expensive work.
    If a cycle overruns one or more ticks, those ticks are recorded and skipped—no
    burst catch-up is attempted. Once an armed session is confirmed closed, exit.
    """
    collected_in_session = False
    scheduled_tick = time.monotonic()
    while True:
        cycle_started = time.monotonic()
        payload = run_cycle(tolerance_seconds=tolerance_seconds)
        scheduler, next_tick = _schedule_after_cycle(
            scheduled_tick=scheduled_tick,
            cycle_started=cycle_started,
            interval_seconds=interval_seconds,
        )
        payload["scheduler"] = scheduler
        print(json.dumps(payload, sort_keys=True), flush=True)

        status = payload.get("status")
        if status == "ok":
            collected_in_session = True
        elif status == "skipped" and collected_in_session:
            return 0

        scheduled_tick = next_tick
        time.sleep(float(scheduler["sleep_seconds"]))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect and resolve GEXY forecasts on anchored target intervals during Alpaca market sessions"
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
