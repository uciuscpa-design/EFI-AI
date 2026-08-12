from datetime import datetime, timezone

from packages.gexy.recording import JsonlRecorder, RecordedSnapshot


def test_recording_round_trip(tmp_path):
    path = tmp_path / "gexy" / "snapshots.jsonl"
    recorder = JsonlRecorder(path)
    snapshot = RecordedSnapshot(
        timestamp=datetime(2026, 8, 11, 20, 0, tzinfo=timezone.utc),
        spot=7750.0,
        total_gex=123.5,
        gamma_flip=7740.0,
        hedge_demand=-42.0,
        positioning_confidence=0.8,
        data_quality="indicative",
        source="alpaca",
    )

    recorder.append(snapshot)
    rows = list(recorder.read())

    assert rows == [snapshot]


def test_append_many_returns_count(tmp_path):
    recorder = JsonlRecorder(tmp_path / "snapshots.jsonl")
    snapshots = [
        RecordedSnapshot(timestamp=datetime(2026, 8, 11, 20, i), spot=7750 + i)
        for i in range(3)
    ]

    assert recorder.append_many(snapshots) == 3
    assert len(list(recorder.read())) == 3
