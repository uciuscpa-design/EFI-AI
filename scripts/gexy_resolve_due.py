from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from packages.gexy.alpaca_calendar import is_alpaca_market_session
from packages.gexy.alpaca_live import AlpacaSpxSnapshotProvider, build_alpaca_market_snapshot
from packages.gexy.due_resolution import due_now
from packages.gexy.prediction_journal import (
    PredictionJournalEntry,
    load_entries,
    resolve_entry,
    rewrite_entries,
)


def _load_due(
    path: Path,
    *,
    observed_at: datetime,
    tolerance_seconds: int,
) -> tuple[list[PredictionJournalEntry], list[PredictionJournalEntry]]:
    entries = load_entries(path)
    eligible = due_now(
        entries,
        observed_at=observed_at,
        tolerance_seconds=tolerance_seconds,
    )
    return entries, eligible


def _resolve_journal(
    path: Path,
    entries: list[PredictionJournalEntry],
    eligible: list[PredictionJournalEntry],
    *,
    observed_at: datetime,
    realized_spot: float,
) -> list[str]:
    if not eligible:
        return []
    eligible_ids = {entry.prediction_id for entry in eligible}
    updated = [
        resolve_entry(entry, resolved_at=observed_at, realized_spot=realized_spot)
        if entry.prediction_id in eligible_ids
        else entry
        for entry in entries
    ]
    rewrite_entries(path, updated)
    return sorted(eligible_ids)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve GEXY production and fine-shadow forecasts only near their exact due time"
    )
    parser.add_argument("--journal", default="data/gexy/live_predictions.jsonl")
    parser.add_argument("--shadow-journal", default="data/gexy/shadow_predictions.jsonl")
    parser.add_argument("--no-shadow", action="store_true", help="resolve only the production journal")
    parser.add_argument("--tolerance-seconds", type=int, default=90)
    args = parser.parse_args()

    observed_at = datetime.now(timezone.utc)
    if not is_alpaca_market_session(observed_at):
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "outside_alpaca_market_session",
                    "observed_at": observed_at.isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    production_path = Path(args.journal)
    production_entries, production_due = _load_due(
        production_path,
        observed_at=observed_at,
        tolerance_seconds=args.tolerance_seconds,
    )

    shadow_path = Path(args.shadow_journal)
    if args.no_shadow:
        shadow_entries: list[PredictionJournalEntry] = []
        shadow_due: list[PredictionJournalEntry] = []
    else:
        shadow_entries, shadow_due = _load_due(
            shadow_path,
            observed_at=observed_at,
            tolerance_seconds=args.tolerance_seconds,
        )

    if not production_due and not shadow_due:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "observed_at": observed_at.isoformat(),
                    "resolved": 0,
                    "production_resolved": 0,
                    "shadow_resolved": 0,
                    "reason": "no_forecasts_due_within_tolerance",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    snapshot, quote_times = build_alpaca_market_snapshot(
        AlpacaSpxSnapshotProvider(),
        observation_time=observed_at,
    )

    production_ids = _resolve_journal(
        production_path,
        production_entries,
        production_due,
        observed_at=observed_at,
        realized_spot=snapshot.spot,
    )
    shadow_ids = (
        []
        if args.no_shadow
        else _resolve_journal(
            shadow_path,
            shadow_entries,
            shadow_due,
            observed_at=observed_at,
            realized_spot=snapshot.spot,
        )
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "observed_at": observed_at.isoformat(),
                "realized_spot": snapshot.spot,
                "quote_count": len(quote_times),
                "resolved": len(production_ids) + len(shadow_ids),
                "production_resolved": len(production_ids),
                "shadow_resolved": len(shadow_ids),
                "production_resolved_ids": production_ids,
                "shadow_resolved_ids": shadow_ids,
                "tolerance_seconds": args.tolerance_seconds,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
