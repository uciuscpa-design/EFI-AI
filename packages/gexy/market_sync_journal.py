from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable

from .market_sync import SynchronizedMarketPair, datetime_to_unix_ns, pair_to_record


@dataclass(frozen=True)
class SyncCoverageSummary:
    total: int
    matched: int
    stale_reference: int
    missing_reference: int
    scoreable: int
    scoreable_fraction: float
    mean_reference_lag_seconds: float | None
    max_reference_lag_seconds: float | None
    p95_reference_lag_seconds: float | None
    lookahead_violations: int
    provenance_flag_violations: int
    timestamp_consistency_violations: int


def append_sync_pair(path: str | Path, pair: SynchronizedMarketPair) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(pair_to_record(pair), sort_keys=True) + "\n")


def load_sync_records(path: str | Path) -> list[dict[str, object]]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("market sync journal rows must be JSON objects")
        rows.append(payload)
    return rows


def _percentile_nearest_rank(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * fraction + 0.999999999) - 1)))
    return ordered[index]


def _timestamp(payload: object, key: str) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get(key)
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return None
    return parsed


def _event_time_ns(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    raw_ns = payload.get("observed_at_ns")
    if raw_ns is not None:
        try:
            value = int(raw_ns)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None
    timestamp = _timestamp(payload, "observed_at")
    return None if timestamp is None else datetime_to_unix_ns(timestamp)


def _timestamp_consistent(payload: object) -> bool:
    if not isinstance(payload, dict):
        return True
    raw_ns = payload.get("observed_at_ns")
    if raw_ns is None:
        return True  # legacy microsecond-only rows remain readable
    timestamp = _timestamp(payload, "observed_at")
    if timestamp is None:
        return False
    try:
        event_ns = int(raw_ns)
    except (TypeError, ValueError):
        return False
    return event_ns > 0 and event_ns // 1_000 == datetime_to_unix_ns(timestamp) // 1_000


def summarize_sync_records(records: Iterable[dict[str, object]]) -> SyncCoverageSummary:
    rows = list(records)
    matched = sum(row.get("status") == "matched" for row in rows)
    stale = sum(row.get("status") == "stale_reference" for row in rows)
    missing = sum(row.get("status") == "missing_reference" for row in rows)
    scoreable = sum(bool(row.get("scoreable")) for row in rows)

    lags = [
        float(row["reference_lag_seconds"])
        for row in rows
        if row.get("reference_lag_seconds") is not None
    ]

    lookahead_violations = 0
    provenance_flag_violations = 0
    timestamp_consistency_violations = 0
    for row in rows:
        if row.get("no_lookahead_enforced") is not True:
            provenance_flag_violations += 1

        primary_payload = row.get("primary")
        reference_payload = row.get("reference")
        if not _timestamp_consistent(primary_payload):
            timestamp_consistency_violations += 1
        if reference_payload is not None and not _timestamp_consistent(reference_payload):
            timestamp_consistency_violations += 1

        primary_ns = _event_time_ns(primary_payload)
        reference_ns = _event_time_ns(reference_payload)
        if primary_ns is not None and reference_ns is not None and reference_ns > primary_ns:
            lookahead_violations += 1

    return SyncCoverageSummary(
        total=len(rows),
        matched=matched,
        stale_reference=stale,
        missing_reference=missing,
        scoreable=scoreable,
        scoreable_fraction=(scoreable / len(rows)) if rows else 0.0,
        mean_reference_lag_seconds=mean(lags) if lags else None,
        max_reference_lag_seconds=max(lags) if lags else None,
        p95_reference_lag_seconds=_percentile_nearest_rank(lags, 0.95),
        lookahead_violations=lookahead_violations,
        provenance_flag_violations=provenance_flag_violations,
        timestamp_consistency_violations=timestamp_consistency_violations,
    )


def build_sync_coverage_report(path: str | Path) -> dict[str, object]:
    summary = summarize_sync_records(load_sync_records(path))
    integrity_ok = (
        summary.lookahead_violations == 0
        and summary.provenance_flag_violations == 0
        and summary.timestamp_consistency_violations == 0
    )
    return {
        "status": "ok" if integrity_ok else "integrity_failure",
        "journal": str(path),
        "summary": asdict(summary),
        "production_feature_enabled": False,
        "production_predictor_changed": False,
        "execution_authorized": False,
        "interpretation": [
            "This report measures synchronization integrity and coverage only; it does not establish predictive value.",
            "Only matched scoreable rows are eligible for a later versioned ES-derived research hypothesis.",
            "Any future-reference timestamp, including a sub-microsecond future timestamp, is a hard lookahead violation.",
            "Raw nanosecond timestamps must agree with their human-readable datetime projection at microsecond precision.",
        ],
    }
