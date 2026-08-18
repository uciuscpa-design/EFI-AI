from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path


HEARTBEAT_SECONDS = 30.0
TARGET_SCRIPT = Path(__file__).with_name("gexy_multiday_causal_intraday.py")


def _pump_output(stream: object) -> None:
    for line in stream:  # type: ignore[union-attr]
        print(line, end="", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen GEXY causal-intraday evaluator with periodic progress heartbeats."
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to gexy_multiday_causal_intraday.py")
    parsed = parser.parse_args()

    forwarded = list(parsed.args)
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]

    command = [sys.executable, str(TARGET_SCRIPT), *forwarded]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout is None:
        raise SystemExit("failed to capture causal evaluator output")

    pump = threading.Thread(target=_pump_output, args=(process.stdout,), daemon=True)
    pump.start()

    while True:
        try:
            return_code = process.wait(timeout=HEARTBEAT_SECONDS)
            break
        except subprocess.TimeoutExpired:
            elapsed_minutes = (time.monotonic() - started) / 60.0
            print(
                f"HEARTBEAT causal-intraday still running: elapsed={elapsed_minutes:.1f}m pid={process.pid}",
                flush=True,
            )

    pump.join(timeout=5.0)
    elapsed_minutes = (time.monotonic() - started) / 60.0
    print(
        f"CAUSAL-INTRADAY PROCESS EXITED: code={return_code} elapsed={elapsed_minutes:.1f}m pid={process.pid}",
        flush=True,
    )
    raise SystemExit(return_code)


if __name__ == "__main__":
    main()
