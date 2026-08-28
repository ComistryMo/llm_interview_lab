from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import pytest

from llm_interview_lab.ai.codex_backend import discover_codex_executable
from llm_interview_lab.desktop import runtime


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _seed_standalone(root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LLM_LAB_PACKAGED", "1")
    monkeypatch.setenv("LLM_LAB_BUNDLE_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(root))
    return runtime.prepare_desktop_repository()


def test_packaged_workspace_accepts_spaces_and_unicode_without_using_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "应用 数据" / "LLM Interview Lab"
    root = _seed_standalone(destination, monkeypatch)
    assert root == destination.resolve()
    assert (root / runtime.STANDALONE_MARKER).is_file()
    assert (root / "workspace/profiles").is_dir()
    assert not any((root / "workspace/profiles").iterdir())


def test_qstandardpaths_is_the_default_for_packaged_desktop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = tmp_path / "platform app data"
    monkeypatch.delenv("LLM_LAB_DESKTOP_DATA_ROOT", raising=False)
    monkeypatch.setattr(runtime, "_qt_app_data_root", lambda: expected)
    assert runtime.desktop_data_root() == expected


def test_alpha1_migration_is_explicit_sha_verified_and_non_destructive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = _seed_standalone(tmp_path / "new data", monkeypatch)
    source = tmp_path / "old data"
    profile = source / "workspace/profiles/旧档案"
    (profile / "submissions/FND-001/attempt-0001").mkdir(parents=True)
    (source / runtime.STANDALONE_MARKER).write_text(
        json.dumps({"schema_version": 1, "version": "0.4.0a1", "synthetic": True}),
        encoding="utf-8",
    )
    (profile / "profile.yaml").write_text("profile_id: old\n", encoding="utf-8")
    (profile / "events.jsonl").write_text("", encoding="utf-8")
    answer = profile / "submissions/FND-001/attempt-0001/submission.py"
    answer.write_text("# private local answer\n", encoding="utf-8")
    monkeypatch.setenv("LLM_LAB_LEGACY_DESKTOP_DATA_ROOT", str(source))

    assert runtime.detect_legacy_desktop_data(destination) == source.resolve()
    source_digest = runtime._tree_sha256(source / "workspace/profiles")
    backup = runtime.migrate_legacy_desktop_data(source, destination)
    migrated = destination / "workspace/profiles"
    assert runtime._tree_sha256(migrated) == source_digest
    assert runtime._tree_sha256(backup / "profiles") == source_digest
    assert answer.read_text(encoding="utf-8") == "# private local answer\n"
    marker = json.loads((destination / runtime.MIGRATION_MARKER).read_text(encoding="utf-8"))
    assert marker["profile_tree_sha256"] == source_digest
    assert str(source) not in json.dumps(marker)
    assert runtime.detect_legacy_desktop_data(destination) is None


def test_migration_refuses_symlinks_and_keeps_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.name == "nt":
        pytest.skip("ordinary Windows users may not have symlink privileges")
    destination = _seed_standalone(tmp_path / "destination", monkeypatch)
    source = tmp_path / "legacy"
    profile = source / "workspace/profiles/sample"
    profile.mkdir(parents=True)
    (source / runtime.STANDALONE_MARKER).write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    (profile / "linked.txt").symlink_to(outside)
    monkeypatch.setenv("LLM_LAB_LEGACY_DESKTOP_DATA_ROOT", str(source))
    with pytest.raises(Exception, match="符号链接"):
        runtime.migrate_legacy_desktop_data(source, destination)
    assert outside.read_text(encoding="utf-8") == "private"


def test_codex_explicit_location_works_without_shell_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / ("codex.cmd" if os.name == "nt" else "codex")
    executable.write_text("echo synthetic\n", encoding="utf-8")
    if os.name != "nt":
        executable.chmod(0o755)
    monkeypatch.setattr(shutil, "which", lambda _: None)
    assert discover_codex_executable(executable) == str(executable.resolve())
    monkeypatch.setenv("APPDATA", str(tmp_path / "empty-appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "empty-localdata"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "empty-home"))
    assert discover_codex_executable(tmp_path / "missing") is None
