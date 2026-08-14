from datetime import datetime, timedelta, timezone

from packages.gexy.session_cadence import summarize_cadence, summarize_scheduler_execution

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


def test_scheduler_execution_report_quantifies_overruns_and_missed_ticks():
    payloads = [
        {
            "scheduler": {
                "target_interval_seconds": 60,
                "cycle_elapsed_seconds": 15,
                "start_lag_seconds": 0,
                "overrun_seconds": 0,
                "missed_intervals": 0,
                "sleep_seconds": 45,
            }
        },
        {
            "scheduler": {
                "target_interval_seconds": 60,
                "cycle_elapsed_seconds": 75,
                "start_lag_seconds": 2,
                "overrun_seconds": 15,
                "missed_intervals": 1,
                "sleep_seconds": 43,
            }
        },
        {
            "scheduler": {
                "target_interval_seconds": 60,
                "cycle_elapsed_seconds": 30,
                "start_lag_seconds": 1,
                "overrun_seconds": 0,
                "missed_intervals": 0,
                "sleep_seconds": 29,
            }
        },
    ]

    report = summarize_scheduler_execution(payloads)

    assert report.cycles_with_scheduler_metrics == 3
    assert report.target_interval_seconds == 60.0
    assert report.mean_cycle_seconds == 40.0
    assert report.median_cycle_seconds == 30.0
    assert report.p90_cycle_seconds == 75.0
    assert report.max_cycle_seconds == 75.0
    assert report.overrun_cycles == 1
    assert report.overrun_cycle_fraction == 1 / 3
    assert report.missed_intervals_total == 1
    assert report.max_missed_intervals_single_cycle == 1
    assert report.mean_start_lag_seconds == 1.0
    assert report.p90_start_lag_seconds == 2.0
    assert report.max_start_lag_seconds == 2.0
    assert report.mean_sleep_seconds == 39.0


def test_scheduler_execution_report_handles_pre_instrumentation_logs():
    report = summarize_scheduler_execution([{"status": "ok"}, {"status": "skipped"}])

    assert report.cycles_with_scheduler_metrics == 0
    assert report.target_interval_seconds is None
    assert report.mean_cycle_seconds is None
    assert report.overrun_cycle_fraction is None
    assert report.missed_intervals_total == 0


def test_scheduler_execution_ignores_partially_malformed_records():
    payloads = [
        {"scheduler": {"target_interval_seconds": 60, "cycle_elapsed_seconds": 10}},
        {
            "scheduler": {
                "target_interval_seconds": 60,
                "cycle_elapsed_seconds": 20,
                "start_lag_seconds": 0,
                "overrun_seconds": 0,
                "missed_intervals": 0,
                "sleep_seconds": 40,
            }
        },
    ]

    report = summarize_scheduler_execution(payloads)

    assert report.cycles_with_scheduler_metrics == 1
    assert report.mean_cycle_seconds == 20.0
