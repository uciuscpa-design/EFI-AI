from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = (
    Path("data/gexy/live_predictions.jsonl"),
    Path("data/gexy/shadow_predictions.jsonl"),
    Path("data/gexy/gax_shadow.jsonl"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _line_count(path: Path) -> int:
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def _git_head() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def snapshot_session(
    *,
    session_date: str,
    destination_root: str | Path = "projects/gexy/snapshots",
    gap_start: str | None = None,
    gap_end: str | None = None,
    note: str | None = None,
    force: bool = False,
    root: Path = ROOT,
) -> dict[str, object]:
    date.fromisoformat(session_date)
    destination = (root / destination_root / session_date).resolve()
    if destination.exists() and not force:
        raise FileExistsError(f"snapshot already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    source_paths = [root / source for source in DEFAULT_SOURCES]
    log_path = root / "data" / "gexy" / "logs" / f"session-{session_date}.log"
    if log_path.exists():
        source_paths.append(log_path)

    files: list[dict[str, object]] = []
    for source in source_paths:
        if not source.exists():
            files.append({
                "source": str(source.relative_to(root)),
                "present": False,
            })
            continue
        target = destination / source.name
        shutil.copy2(source, target)
        files.append({
            "source": str(source.relative_to(root)),
            "snapshot": str(target.relative_to(root)),
            "present": True,
            "bytes": target.stat().st_size,
            "lines": _line_count(target),
            "sha256": _sha256(target),
        })

    gaps: list[dict[str, str]] = []
    if gap_start or gap_end:
        if not gap_start or not gap_end:
            raise ValueError("gap_start and gap_end must be supplied together")
        gaps.append({"start": gap_start, "end": gap_end, "reason": "connectivity_outage"})

    metadata: dict[str, object] = {
        "schema_version": 1,
        "session_date": session_date,
        "git_head": _git_head(),
        "files": files,
        "known_data_gaps": gaps,
        "note": note,
        "research_only": True,
        "production_model_changed_during_session": False,
    }
    metadata_path = destination / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metadata["metadata_path"] = str(metadata_path.relative_to(root))
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze a dated GEXY research-session snapshot")
    parser.add_argument("--session-date", required=True, help="session date in YYYY-MM-DD")
    parser.add_argument("--destination-root", default="projects/gexy/snapshots")
    parser.add_argument("--gap-start")
    parser.add_argument("--gap-end")
    parser.add_argument("--note")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        report = snapshot_session(
            session_date=args.session_date,
            destination_root=args.destination_root,
            gap_start=args.gap_start,
            gap_end=args.gap_end,
            note=args.note,
            force=args.force,
        )
    except (FileExistsError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 2

    print(json.dumps({"status": "ok", **report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
