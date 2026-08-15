from datetime import datetime, timedelta, timezone

from packages.gexy.market_sync import (
    MarketObservation,
    datetime_to_unix_ns,
    synchronize_primary_with_reference,
)
from packages.gexy.market_sync_journal import (
    append_sync_pair,
    build_sync_coverage_report,
    load_sync_records,
    summarize_sync_records,
)


def _observation(symbol: str, seconds: float, price: float, kind: str) -> MarketObservation:
    base = datetime(2026, 8, 17, 13, 30, tzinfo=timezone.utc)
    observed_at = base + timedelta(seconds=seconds)
    return MarketObservation(
        symbol=symbol,
        instrument_type=kind,
        price=price,
        observed_at=observed_at,
        received_at=observed_at + timedelta(milliseconds=200),
        source="test-provider",
    )


def test_append_load_and_summarize_sync_coverage(tmp_path):
    journal = tmp_path / "spx_es_sync.jsonl"
    primary_1 = _observation("SPX", 10.0, 7600.0, "cash_index_inferred")
    primary_2 = _observation("SPX", 20.0, 7601.0, "cash_index_inferred")
    primary_3 = _observation("SPX", 30.0, 7602.0, "cash_index_inferred")

    append_sync_pair(
        journal,
        synchronize_primary_with_reference(
            primary_1,
            [_observation("ESU6", 9.5, 7610.0, "future")],
            max_lag_seconds=5.0,
        ),
    )
    append_sync_pair(
        journal,
        synchronize_primary_with_reference(
            primary_2,
            [_observation("ESU6", 10.0, 7611.0, "future")],
            max_lag_seconds=5.0,
        ),
    )
    append_sync_pair(
        journal,
        synchronize_primary_with_reference(
            primary_3,
            [_observation("ESU6", 31.0, 7612.0, "future")],
            max_lag_seconds=5.0,
        ),
    )

    records = load_sync_records(journal)
    summary = summarize_sync_records(records)

    assert summary.total == 3
    assert summary.matched == 1
    assert summary.stale_reference == 1
    assert summary.missing_reference == 1
    assert summary.scoreable == 1
    assert summary.scoreable_fraction == 1 / 3
    assert summary.mean_reference_lag_seconds == 5.25
    assert summary.max_reference_lag_seconds == 10.0
    assert summary.p95_reference_lag_seconds == 10.0
    assert summary.lookahead_violations == 0
    assert summary.provenance_flag_violations == 0
    assert summary.timestamp_consistency_violations == 0


def test_report_marks_manually_corrupted_future_reference_as_integrity_failure(tmp_path):
    journal = tmp_path / "corrupt.jsonl"
    journal.write_text(
        '{"status":"matched","scoreable":true,"no_lookahead_enforced":true,'
        '"reference_lag_seconds":-1.0,'
        '"primary":{"observed_at":"2026-08-17T13:30:10+00:00"},'
        '"reference":{"observed_at":"2026-08-17T13:30:11+00:00"}}\n',
        encoding="utf-8",
    )

    report = build_sync_coverage_report(journal)

    assert report["status"] == "integrity_failure"
    assert report["summary"]["lookahead_violations"] == 1
    assert report["production_feature_enabled"] is False
    assert report["execution_authorized"] is False


def test_report_detects_submicrosecond_future_reference_with_same_iso_projection(tmp_path):
    journal = tmp_path / "submicrosecond-corrupt.jsonl"
    observed_at = datetime(2026, 8, 17, 13, 30, 10, 123456, tzinfo=timezone.utc)
    primary_ns = datetime_to_unix_ns(observed_at)
    journal.write_text(
        '{"status":"matched","scoreable":true,"no_lookahead_enforced":true,'
        '"reference_lag_seconds":0.0,'
        f'"primary":{{"observed_at":"{observed_at.isoformat()}","observed_at_ns":{primary_ns}}},'
        f'"reference":{{"observed_at":"{observed_at.isoformat()}","observed_at_ns":{primary_ns + 1}}}}}\n',
        encoding="utf-8",
    )

    report = build_sync_coverage_report(journal)

    assert report["status"] == "integrity_failure"
    assert report["summary"]["lookahead_violations"] == 1
    assert report["summary"]["timestamp_consistency_violations"] == 0


def test_report_detects_raw_nanosecond_timestamp_inconsistent_with_iso_projection(tmp_path):
    journal = tmp_path / "timestamp-corrupt.jsonl"
    observed_at = datetime(2026, 8, 17, 13, 30, 10, 123456, tzinfo=timezone.utc)
    observed_ns = datetime_to_unix_ns(observed_at)
    journal.write_text(
        '{"status":"missing_reference","scoreable":false,"no_lookahead_enforced":true,'
        '"reference_lag_seconds":null,'
        f'"primary":{{"observed_at":"{observed_at.isoformat()}","observed_at_ns":{observed_ns + 1000}}},'
        '"reference":null}\n',
        encoding="utf-8",
    )

    report = build_sync_coverage_report(journal)

    assert report["status"] == "integrity_failure"
    assert report["summary"]["timestamp_consistency_violations"] == 1
    assert report["summary"]["lookahead_violations"] == 0


def test_empty_sync_report_is_safe_and_does_not_enable_features(tmp_path):
    journal = tmp_path / "missing.jsonl"

    report = build_sync_coverage_report(journal)

    assert report["status"] == "ok"
    assert report["summary"]["total"] == 0
    assert report["summary"]["scoreable_fraction"] == 0.0
    assert report["summary"]["timestamp_consistency_violations"] == 0
    assert report["production_feature_enabled"] is False
    assert report["production_predictor_changed"] is False
    assert report["execution_authorized"] is False
