from __future__ import annotations

import subprocess
from pathlib import Path


MAX_OUTPUT_CHARS = 16_000
MAX_READ_CHARS = 24_000
SAFE_TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml"}
FORBIDDEN_NAME_PARTS = {
    ".env",
    "credential",
    "credentials",
    "secret",
    "secrets",
    "token",
    "apikey",
    "api_key",
    "private_key",
}

SAFE_COMMANDS: dict[str, tuple[str, ...]] = {
    "git_status": ("git", "status", "--short", "--branch"),
    "git_head": ("git", "rev-parse", "--short", "HEAD"),
    "git_recent": ("git", "log", "-8", "--oneline", "--decorate"),
}


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def _run(argv: list[str], *, cwd: Path, timeout: int = 120) -> str:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return _truncate(
        f"return_code={completed.returncode}\n"
        f"stdout:\n{stdout}\n"
        f"stderr:\n{stderr}"
    )


def run_safe_action(action: str, *, repo_root: Path | None = None) -> str:
    root = (repo_root or Path.cwd()).resolve()
    argv = SAFE_COMMANDS.get(action)
    if argv is None:
        allowed = ", ".join(sorted(SAFE_COMMANDS))
        return f"BLOCKED: unknown action {action!r}. Allowed actions: {allowed}"
    return _run(list(argv), cwd=root, timeout=60)


def _contains_forbidden_name(path: Path) -> bool:
    lowered_parts = [part.lower() for part in path.parts]
    for part in lowered_parts:
        if any(marker in part for marker in FORBIDDEN_NAME_PARTS):
            return True
    return False


def _resolve_repo_file(repo_root: Path, relative_path: str) -> Path:
    root = repo_root.resolve()
    requested = Path(relative_path)
    if requested.is_absolute():
        raise ValueError("absolute paths are not allowed")
    candidate = (root / requested).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes the repository") from exc
    if _contains_forbidden_name(requested):
        raise ValueError("secret-bearing or credential-like paths are blocked")
    if candidate.suffix.lower() not in SAFE_TEXT_SUFFIXES:
        raise ValueError(f"file type {candidate.suffix!r} is not allowed")
    if not candidate.is_file():
        raise ValueError("file does not exist")
    return candidate


def read_repo_file(relative_path: str, *, repo_root: Path | None = None) -> str:
    root = (repo_root or Path.cwd()).resolve()
    try:
        path = _resolve_repo_file(root, relative_path)
    except ValueError as exc:
        return f"BLOCKED: {exc}"
    text = path.read_text(encoding="utf-8", errors="replace")
    return _truncate(text, MAX_READ_CHARS)


def _validate_gexy_test_file(test_file: str) -> str:
    path = Path(test_file)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("test path must stay inside tests/")
    normalized = path.as_posix()
    if not normalized.startswith("tests/test_gexy_") or not normalized.endswith(".py"):
        raise ValueError("only tests/test_gexy_*.py files are allowed")
    if any(ch.isspace() for ch in normalized):
        raise ValueError("whitespace is not allowed in test paths")
    return normalized


def run_gexy_test(test_file: str, *, repo_root: Path | None = None) -> str:
    root = (repo_root or Path.cwd()).resolve()
    try:
        normalized = _validate_gexy_test_file(test_file)
    except ValueError as exc:
        return f"BLOCKED: {exc}"
    if not (root / normalized).is_file():
        return "BLOCKED: requested test file does not exist"
    argv = ["uv", "run", "--with", "pytest", "pytest", normalized, "-q"]
    return _run(argv, cwd=root, timeout=300)
