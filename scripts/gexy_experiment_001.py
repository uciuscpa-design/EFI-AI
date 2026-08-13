from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from packages.gexy.alpaca_provider import AlpacaSpxSnapshotProvider
from packages.gexy.capture import capture_feature_state
from packages.gexy.recording import JsonlRecorder

ET = ZoneInfo("America/New_York")
DEFAULT_OUTPUT = Path("projects/gexy/experiments/experiment_001_intraday.jsonl")


def _session_bounds(now_utc: datetime) -> tuple[datetime, datetime]:
    local = now_utc.astimezone(ET)
    open_local = local.replace(hour=9, minute=30, second=0, microsecond=0)
    close_local = local.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_local.astimezone(timezone.utc), close_local.astimezone(timezone.utc)


def _record_once(
    provider: AlpacaSpxSnapshotProvider,
    recorder: JsonlRecorder,
    *,
    max_quote_age_seconds: float,
) -> str:
    scheduled = datetime.now(timezone.utc)
    observation = provider(scheduled)
    result = capture_feature_state(
        recorder,
        observation_time=observation.timestamp,
        spot=observation.spot,
        feature_state=observation.feature_state,
        option_quote_times=observation.quote_times,
        source="alpaca_indicative",
        max_quote_age_seconds=max_quote_age_seconds,
    )
    return f"{observation.timestamp.isoformat()} recorded={result.recorded} quality={result.data_quality} spot={observation.spot:.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GEXY Experiment 001 intraday SPX capture")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--max-quote-age-seconds", type=float, default=90.0)
    parser.add_argument("--once", action="store_true", help="Attempt one capture immediately and exit")
    args = parser.parse_args()

    if args.interval_seconds <= 0:
        raise SystemExit("--interval-seconds must be positive")
    if args.max_quote_age_seconds <= 0:
        raise SystemExit("--max-quote-age-seconds must be positive")

    provider = AlpacaSpxSnapshotProvider()
    recorder = JsonlRecorder(args.output)

    if args.once:
        print(_record_once(provider, recorder, max_quote_age_seconds=args.max_quote_age_seconds))
        return 0

    now = datetime.now(timezone.utc)
    session_open, session_close = _session_bounds(now)
    if now < session_open or now > session_close:
        local_now = now.astimezone(ET)
        raise SystemExit(
            f"regular SPX session is closed at {local_now.isoformat()}; "
            "use --once only for a freshness-gate diagnostic"
        )

    next_tick = now
    while next_tick <= session_close:
        sleep_seconds = (next_tick - datetime.now(timezone.utc)).total_seconds()
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        try:
            print(_record_once(provider, recorder, max_quote_age_seconds=args.max_quote_age_seconds), flush=True)
        except Exception as exc:  # keep the experiment running while making failures visible
            print(f"{datetime.now(timezone.utc).isoformat()} capture_error={type(exc).__name__}: {exc}", flush=True)
        next_tick += timedelta(seconds=args.interval_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
