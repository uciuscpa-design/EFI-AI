from datetime import datetime, timedelta, timezone

from packages.gexy.session_cadence import summarize_cadence

BASE = datetime(2026, 8, 14, 14, 0, tzinfo=timezone.utc)


def test_cadence_report_quantifies_target_coverage_and_gaps():
    offsets = [0, 60, 122, 242, 602]
    times = [BASE + timedelta(seconds=value) for value in offsets]

    report = summarize_cadence(times, target_interval_seconds=60)

    assert report.observations == 5
    assert report.intervals == 4
    assert report.median_interval_seconds == 91.0
    assert report.p90_interval_seconds == 360.0
    assert report.max_interval_seconds == 360.0
    assert report.intervals_over_90_seconds == 2
    assert report.intervals_over_180_seconds == 1
    assert report.intervals_within_target_plus_30_seconds == 2
    assert report.target_plus_30_coverage == 0.5
    assert report.largest_gaps[0].seconds == 360.0


def test_cadence_report_handles_single_observation():
    report = summarize_cadence([BASE])

    assert report.observations == 1
    assert report.intervals == 0
    assert report.mean_interval_seconds is None
    assert report.target_plus_30_coverage is None
    assert report.largest_gaps == ()


def test_cadence_rejects_naive_timestamps():
    try:
        summarize_cadence([datetime(2026, 8, 14, 14, 0)])
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected ValueError")
