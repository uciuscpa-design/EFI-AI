from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from packages.gexy.recording import JsonlRecorder
from packages.gexy.sampler import SampleInput, run_sampler, sampling_schedule


def test_sampling_schedule_is_inclusive_and_deterministic():
    start = datetime(2026, 8, 13, 13, 30, tzinfo=timezone.utc)
    end = start + timedelta(minutes=2)
    schedule = sampling_schedule(start=start, end=end, interval_seconds=60)
    assert schedule == (start, start + timedelta(minutes=1), end)


def test_sampler_records_fresh_samples(tmp_path):
    recorder = JsonlRecorder(tmp_path / "gexy.jsonl")
    start = datetime(2026, 8, 13, 13, 30, tzinfo=timezone.utc)

    def provider(t):
        observed = t + timedelta(seconds=2)
        return SampleInput(
            observation_time=observed,
            spot=7750.0,
            feature_state=SimpleNamespace(
                total_gex=1.0,
                gamma_flip=7740.0,
                hedge_pressure=SimpleNamespace(total_pressure=2.0, confidence=0.8),
                data_quality="live",
            ),
            option_quote_times=(observed - timedelta(seconds=10),),
        )

    events = run_sampler(recorder, schedule=(start,), provider=provider)
    assert events[0].result.recorded is True
    assert len(list(recorder.read())) == 1


def test_sampler_rejects_pre_schedule_observation(tmp_path):
    recorder = JsonlRecorder(tmp_path / "gexy.jsonl")
    start = datetime(2026, 8, 13, 13, 30, tzinfo=timezone.utc)

    def provider(t):
        return SampleInput(
            observation_time=t - timedelta(seconds=1),
            spot=7750.0,
            feature_state=SimpleNamespace(),
            option_quote_times=(t - timedelta(seconds=1),),
        )

    events = run_sampler(recorder, schedule=(start,), provider=provider)
    assert events[0].result.recorded is False
    assert events[0].result.data_quality == "pre_schedule"
    assert list(recorder.read()) == []
