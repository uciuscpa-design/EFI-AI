from pathlib import Path

import pytest

from packages.bridge import _resolve_repo_file, _validate_gexy_test_file, read_repo_file, run_safe_action


def test_resolve_repo_file_allows_normal_text_file(tmp_path: Path) -> None:
    path = tmp_path / "docs" / "note.md"
    path.parent.mkdir()
    path.write_text("hello", encoding="utf-8")

    resolved = _resolve_repo_file(tmp_path, "docs/note.md")

    assert resolved == path.resolve()


def test_resolve_repo_file_blocks_secret_like_paths(tmp_path: Path) -> None:
    secret = tmp_path / ".env"
    secret.write_text("OPENAI_API_KEY=do-not-read", encoding="utf-8")

    with pytest.raises(ValueError, match="blocked|secret|credential"):
        _resolve_repo_file(tmp_path, ".env")


def test_resolve_repo_file_blocks_repo_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.md"
    outside.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes"):
        _resolve_repo_file(tmp_path, "../outside.md")


def test_validate_gexy_test_file_accepts_only_frozen_shape() -> None:
    assert _validate_gexy_test_file("tests/test_gexy_tradeflow.py") == "tests/test_gexy_tradeflow.py"

    with pytest.raises(ValueError):
        _validate_gexy_test_file("tests/test_other.py")
    with pytest.raises(ValueError):
        _validate_gexy_test_file("../tests/test_gexy_tradeflow.py")
    with pytest.raises(ValueError):
        _validate_gexy_test_file("tests/test_gexy_tradeflow.py -x")


def test_unknown_repo_action_is_blocked_without_shell_execution(tmp_path: Path) -> None:
    result = run_safe_action("rm_everything", repo_root=tmp_path)
    assert result.startswith("BLOCKED:")


def test_read_repo_file_does_not_expose_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("TOP_SECRET", encoding="utf-8")
    result = read_repo_file(".env", repo_root=tmp_path)
    assert result.startswith("BLOCKED:")
    assert "TOP_SECRET" not in result
