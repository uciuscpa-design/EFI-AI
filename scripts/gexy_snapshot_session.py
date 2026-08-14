from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = (
    Path("data/gexy/live_predictions.jsonl"),
    Path("data/gexy/shadow_predictions.jsonl"),
    Path("data/gexy/gax_shadow.jsonl"),
)
_LIFECYCLE_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+GEXY session collector (?P<event>starting|exited code=(?P<code>-?\d+))\s*$",
    re.MULTILINE,
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


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


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


def _json_objects_from_text(text: str) -> Iterator[dict[str, object]]:
    """Yield complete JSON objects embedded in mixed/plain-text collector logs."""
    decoder = json.JSONDecoder()
    cursor = 0
    while True:
        start = text.find("{", cursor)
        if start < 0:
            return
        try:
            payload, consumed = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            cursor = start + 1
            continue
        cursor = start + consumed
        if isinstance(payload, dict):
            yield payload


def _timestamp_from_payload(payload: dict[str, object]) -> datetime | None:
    value = payload.get("observed_at")
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.tzinfo is not None else None


def _observed_times_from_log(path: Path) -> list[datetime]:
    """Read collector-cycle timestamps from the actual mixed log format.

    The live launcher writes one compact JSON object per collector cycle, mixed
    with plain-text lifecycle lines. Prefer exact per-line JSON parsing so braces
    inside nested payloads cannot confuse the generic scanner. Keep the scanner
    only as a compatibility fallback for older multiline JSON logs.
    """
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8", errors="replace")
    observed: list[datetime] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        timestamp = _timestamp_from_payload(payload)
        if timestamp is not None:
            observed.append(timestamp)

    if not observed:
        for payload in _json_objects_from_text(text):
            timestamp = _timestamp_from_payload(payload)
            if timestamp is not None:
                observed.append(timestamp)

    return sorted(set(observed))


def _detect_observation_gaps(path: Path, *, threshold_seconds: int = 180) -> list[dict[str, object]]:
    observed = _observed_times_from_log(path)
    gaps: list[dict[str, object]] = []
    for previous, current in zip(observed, observed[1:]):
        seconds = (current - previous).total_seconds()
        if seconds > threshold_seconds:
            gaps.append(
                {
                    "start": previous.isoformat(),
                    "end": current.isoformat(),
                    "duration_seconds": seconds,
                    "reason": "observation_gap_detected",
                }
            )
    return gaps


def _detect_lifecycle_gaps(path: Path, *, threshold_seconds: int = 180) -> list[dict[str, object]]:
    """Detect downtime between a recorded collector exit and its next restart."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    events: list[tuple[datetime, str, int | None]] = []
    for match in _LIFECYCLE_PATTERN.finditer(text):
        try:
            timestamp = datetime.fromisoformat(match.group("timestamp").replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp.tzinfo is None:
            continue
        code = match.group("code")
        events.append((timestamp, match.group("event"), None if code is None else int(code)))
    events.sort(key=lambda row: row[0])

    gaps: list[dict[str, object]] = []
    last_exit: tuple[datetime, int | None] | None = None
    for timestamp, event, code in events:
        if event.startswith("exited code="):
            last_exit = (timestamp, code)
            continue
        if event == "starting" and last_exit is not None:
            exited_at, exit_code = last_exit
            seconds = (timestamp - exited_at).total_seconds()
            if seconds > threshold_seconds:
                gaps.append(
                    {
                        "start": exited_at.isoformat(),
                        "end": timestamp.isoformat(),
                        "duration_seconds": seconds,
                        "reason": "collector_restart_gap",
                        "exit_code": exit_code,
                    }
                )
            last_exit = None
    return gaps


def _parse_gap_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return timestamp if timestamp.tzinfo is not None else None


def _combine_detected_gaps(
    lifecycle_gaps: list[dict[str, object]],
    observation_gaps: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Prefer lifecycle evidence when an observation gap overlaps the same downtime."""
    combined = list(lifecycle_gaps)
    for observation in observation_gaps:
        obs_start = _parse_gap_time(observation.get("start"))
        obs_end = _parse_gap_time(observation.get("end"))
        overlaps = False
        if obs_start is not None and obs_end is not None:
            for lifecycle in lifecycle_gaps:
                life_start = _parse_gap_time(lifecycle.get("start"))
                life_end = _parse_gap_time(lifecycle.get("end"))
                if life_start is not None and life_end is not None and obs_start <= life_end and life_start <= obs_end:
                    overlaps = True
                    break
        if not overlaps:
            combined.append(observation)
    combined.sort(key=lambda gap: str(gap.get("start", "")))
    return combined


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
            files.append({"source": _relative_posix(source, root), "present": False})
            continue
        target = destination / source.name
        shutil.copy2(source, target)
        files.append(
            {
                "source": _relative_posix(source, root),
                "snapshot": _relative_posix(target, root),
                "present": True,
                "bytes": target.stat().st_size,
                "lines": _line_count(target),
                "sha256": _sha256(target),
            }
        )

    gaps = _combine_detected_gaps(
        _detect_lifecycle_gaps(log_path),
        _detect_observation_gaps(log_path),
    )
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
    metadata["metadata_path"] = _relative_posix(metadata_path, root)
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
