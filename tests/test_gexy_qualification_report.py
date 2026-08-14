import importlib.util
import json
from datetime import datetime
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gexy_qualification_report.py"
SPEC = importlib.util.spec_from_file_location("gexy_qualification_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_load_snapshot_research_reads_authoritative_close(tmp_path, monkeypatch):
    session_dir = tmp_path / "2026-08-17"
    session_dir.mkdir()
    (session_dir / "shadow_predictions.jsonl").write_text("placeholder\n", encoding="utf-8")
    (session_dir / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "session_date": "2026-08-17",
                "market_session": {
                    "session_date": "2026-08-17",
                    "open_at": "2026-08-17T09:30:00-04:00",
                    "close_at": "2026-08-17T16:00:00-04:00",
                    "source": "alpaca_calendar_collector",
                },
            }
        ),
        encoding="utf-8",
    )
    sentinel = object()
    monkeypatch.setattr(MODULE, "load_entries", lambda _: [sentinel])

    sessions, closes = MODULE._load_snapshot_research(tmp_path)

    assert sessions == {"2026-08-17": [sentinel]}
    assert closes["2026-08-17"] == datetime.fromisoformat("2026-08-17T16:00:00-04:00")
    assert closes["2026-08-17"].tzinfo is not None


def test_legacy_snapshot_without_market_session_stays_conservative(tmp_path, monkeypatch):
    session_dir = tmp_path / "2026-08-14"
    session_dir.mkdir()
    (session_dir / "shadow_predictions.jsonl").write_text("placeholder\n", encoding="utf-8")
    (session_dir / "metadata.json").write_text(
        json.dumps({"schema_version": 1, "session_date": "2026-08-14"}),
        encoding="utf-8",
    )
    sentinel = object()
    monkeypatch.setattr(MODULE, "load_entries", lambda _: [sentinel])

    sessions, closes = MODULE._load_snapshot_research(tmp_path)

    assert sessions == {"2026-08-14": [sentinel]}
    assert closes == {}


def test_mismatched_or_naive_close_metadata_is_ignored(tmp_path, monkeypatch):
    session_dir = tmp_path / "2026-08-17"
    session_dir.mkdir()
    (session_dir / "shadow_predictions.jsonl").write_text("placeholder\n", encoding="utf-8")
    (session_dir / "metadata.json").write_text(
        json.dumps(
            {
                "market_session": {
                    "session_date": "2026-08-16",
                    "close_at": "2026-08-17T16:00:00",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(MODULE, "load_entries", lambda _: [object()])

    _, closes = MODULE._load_snapshot_research(tmp_path)

    assert closes == {}
