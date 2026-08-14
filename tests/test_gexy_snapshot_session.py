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
