from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from packages.gexy.alpaca_live import AlpacaSpxSnapshotProvider, build_alpaca_market_snapshot
from packages.gexy.due_resolution import due_now
from packages.gexy.market_session import is_regular_spx_cash_session
from packages.gexy.prediction_journal import load_entries, resolve_entry, rewrite_entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve GEXY forecasts only near their exact due time")
    parser.add_argument("--journal", default="data/gexy/live_predictions.jsonl")
    parser.add_argument("--tolerance-seconds", type=int, default=90)
    args = parser.parse_args()

    observed_at = datetime.now(timezone.utc)
    if not is_regular_spx_cash_session(observed_at):
        print(json.dumps({"status": "skipped", "reason": "outside_regular_spx_session", "observed_at": observed_at.isoformat()}, indent=2, sort_keys=True))
        return 0

    path = Path(args.journal)
    entries = load_entries(path)
    eligible = due_now(entries, observed_at=observed_at, tolerance_seconds=args.tolerance_seconds)
    if not eligible:
        print(json.dumps({"status": "ok", "observed_at": observed_at.isoformat(), "resolved": 0, "reason": "no_forecasts_due_within_tolerance"}, indent=2, sort_keys=True))
        return 0

    snapshot, quote_times = build_alpaca_market_snapshot(AlpacaSpxSnapshotProvider(), observation_time=observed_at)
    eligible_ids = {entry.prediction_id for entry in eligible}
    updated = [
        resolve_entry(entry, resolved_at=observed_at, realized_spot=snapshot.spot)
        if entry.prediction_id in eligible_ids
        else entry
        for entry in entries
    ]
    rewrite_entries(path, updated)
    print(json.dumps({
        "status": "ok",
        "observed_at": observed_at.isoformat(),
        "realized_spot": snapshot.spot,
        "quote_count": len(quote_times),
        "resolved": len(eligible),
        "resolved_ids": sorted(eligible_ids),
        "tolerance_seconds": args.tolerance_seconds,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
