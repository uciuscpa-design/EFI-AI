import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_snapshot_session.py"
SPEC = importlib.util.spec_from_file_location("gexy_snapshot_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_snapshot_session_copies_and_hashes_research_files(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: "abc123")
    data_dir = tmp_path / "data" / "gexy"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)
    (data_dir / "live_predictions.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    (data_dir / "shadow_predictions.jsonl").write_text('{"b":2}\n{"b":3}\n', encoding="utf-8")
    (data_dir / "gax_shadow.jsonl").write_text('{"c":4}\n', encoding="utf-8")
    (logs_dir / "session-2026-08-14.log").write_text("start\nok\n", encoding="utf-8")

    report = MODULE.snapshot_session(
        session_date="2026-08-14",
        gap_start="2026-08-14T11:01:22-07:00",
        gap_end="2026-08-14T11:48:40-07:00",
        note="connectivity interruption",
        root=tmp_path,
    )

    assert report["git_head"] == "abc123"
    assert report["production_model_changed_during_session"] is False
    assert report["known_data_gaps"][0]["reason"] == "connectivity_outage"
    files = {item["source"]: item for item in report["files"]}
    assert files["data/gexy/live_predictions.jsonl"]["lines"] == 1
    assert files["data/gexy/shadow_predictions.jsonl"]["lines"] == 2
    assert len(files["data/gexy/gax_shadow.jsonl"]["sha256"]) == 64
    metadata = json.loads((tmp_path / report["metadata_path"]).read_text(encoding="utf-8"))
    assert metadata["session_date"] == "2026-08-14"


def _empty_research_files(tmp_path):
    data_dir = tmp_path / "data" / "gexy"
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True)
    for name in ("live_predictions.jsonl", "shadow_predictions.jsonl", "gax_shadow.jsonl"):
        (data_dir / name).write_text("", encoding="utf-8")
    return logs_dir


def _actual_compact_log_text():
    return """{\"observed_at\": \"2026-08-14T17:59:30.000000+00:00\", \"status\": \"ok\", \"prediction\": {\"nested\": true}}
{\"observed_at\": \"2026-08-14T18:00:53.674568+00:00\", \"status\": \"ok\", \"resolution\": {\"observed_at\": \"2026-08-14T18:00:55.743464+00:00\"}}
[2026-08-14T11:48:40.0262366-07:00] GEXY session collector starting
{\"observed_at\": \"2026-08-14T18:50:33.942241+00:00\", \"status\": \"ok\", \"prediction\": {\"nested\": true}}
{\"observed_at\": \"2026-08-14T18:51:40.000000+00:00\", \"status\": \"ok\"}
"""


def _assert_actual_outage_gap(report):
    assert len(report["known_data_gaps"]) == 1
    gap = report["known_data_gaps"][0]
    assert gap["reason"] == "observation_gap_detected"
    assert gap["start"] == "2026-08-14T18:00:53.674568+00:00"
    assert gap["end"] == "2026-08-14T18:50:33.942241+00:00"
    assert abs(gap["duration_seconds"] - 2980.267673) < 1e-6


def test_snapshot_auto_detects_large_observation_gap_from_multiline_json(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    logs_dir = _empty_research_files(tmp_path)
    (logs_dir / "session-2026-08-14.log").write_text(
        """[2026-08-14T10:00:00-07:00] GEXY session collector starting
{
  \"observed_at\": \"2026-08-14T18:01:22+00:00\",
  \"status\": \"ok\"
}
noise between payloads
{
  \"observed_at\": \"2026-08-14T18:02:22+00:00\",
  \"status\": \"ok\"
}
[2026-08-14T11:48:40-07:00] GEXY session collector starting
{
  \"observed_at\": \"2026-08-14T18:48:40+00:00\",
  \"status\": \"ok\"
}
""",
        encoding="utf-8",
    )

    report = MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)

    assert len(report["known_data_gaps"]) == 1
    gap = report["known_data_gaps"][0]
    assert gap["reason"] == "observation_gap_detected"
    assert gap["start"] == "2026-08-14T18:02:22+00:00"
    assert gap["end"] == "2026-08-14T18:48:40+00:00"
    assert gap["duration_seconds"] == 2778.0


def test_snapshot_detects_actual_line_delimited_outage_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    logs_dir = _empty_research_files(tmp_path)
    (logs_dir / "session-2026-08-14.log").write_text(_actual_compact_log_text(), encoding="utf-8")

    report = MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)

    _assert_actual_outage_gap(report)


def test_snapshot_detects_actual_utf16_powershell_outage_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    logs_dir = _empty_research_files(tmp_path)
    (logs_dir / "session-2026-08-14.log").write_text(_actual_compact_log_text(), encoding="utf-16")

    report = MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)

    _assert_actual_outage_gap(report)


def test_snapshot_detects_gap_between_collector_exit_and_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    logs_dir = _empty_research_files(tmp_path)
    (logs_dir / "session-2026-08-14.log").write_text(
        """[2026-08-14T06:20:20.0000000-07:00] GEXY session collector starting
[2026-08-14T11:01:22.0000000-07:00] GEXY session collector exited code=1
[2026-08-14T11:48:48.0000000-07:00] GEXY session collector starting
[2026-08-14T13:00:05.0000000-07:00] GEXY session collector exited code=0
""",
        encoding="utf-8",
    )

    report = MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)

    assert len(report["known_data_gaps"]) == 1
    gap = report["known_data_gaps"][0]
    assert gap["reason"] == "collector_restart_gap"
    assert gap["exit_code"] == 1
    assert gap["start"].startswith("2026-08-14T11:01:22")
    assert gap["end"].startswith("2026-08-14T11:48:48")
    assert gap["duration_seconds"] == 2846.0


def test_lifecycle_gap_takes_precedence_over_overlapping_observation_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    logs_dir = _empty_research_files(tmp_path)
    (logs_dir / "session-2026-08-14.log").write_text(
        """{
  \"observed_at\": \"2026-08-14T18:01:20+00:00\"
}
[2026-08-14T11:01:22-07:00] GEXY session collector exited code=1
[2026-08-14T11:48:48-07:00] GEXY session collector starting
{
  \"observed_at\": \"2026-08-14T18:48:50+00:00\"
}
""",
        encoding="utf-8",
    )

    report = MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)

    assert len(report["known_data_gaps"]) == 1
    assert report["known_data_gaps"][0]["reason"] == "collector_restart_gap"


def test_json_scanner_skips_non_json_braces():
    payloads = list(
        MODULE._json_objects_from_text(
            'prefix {not json} middle {"observed_at":"2026-08-14T18:01:22+00:00"} suffix'
        )
    )
    assert payloads == [{"observed_at": "2026-08-14T18:01:22+00:00"}]


def test_snapshot_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)
    destination = tmp_path / "projects" / "gexy" / "snapshots" / "2026-08-14"
    destination.mkdir(parents=True)

    try:
        MODULE.snapshot_session(session_date="2026-08-14", root=tmp_path)
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected FileExistsError")


def test_snapshot_requires_complete_gap_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(MODULE, "_git_head", lambda: None)

    try:
        MODULE.snapshot_session(
            session_date="2026-08-14",
            gap_start="2026-08-14T11:01:22-07:00",
            root=tmp_path,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
