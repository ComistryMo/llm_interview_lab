from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import stat
import subprocess
import warnings
import zipfile

import pytest

import scripts.export_handoff as exporter
from scripts.export_handoff import (
    ExportError,
    GitSnapshot,
    create_archive,
    main,
    prepare_export,
    verify_archive,
)


pytestmark = [pytest.mark.infrastructure]
TEST_GIT_SHA = "a" * 40
ALLOWLIST_PATH = "config/export/handoff.json"


def _write_allowlist(root: Path, files: list[str]) -> None:
    path = root / ALLOWLIST_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"schema_version": 1, "files": files},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_files(root: Path, files: dict[str, str | bytes]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_bytes(content.encode("utf-8"))


def _snapshot(
    tracked_files: set[str] | frozenset[str],
    *,
    dirty: bool = True,
) -> GitSnapshot:
    return GitSnapshot(
        sha=TEST_GIT_SHA,
        dirty=dirty,
        tracked_files=frozenset(tracked_files),
    )


def _prepare(
    root: Path,
    files: dict[str, str | bytes],
    *,
    allowlisted: list[str] | None = None,
    tracked: set[str] | None = None,
    dirty: bool = True,
):
    _write_files(root, files)
    selected = allowlisted or list(files)
    _write_allowlist(root, selected)
    return prepare_export(
        repo_root=root,
        allowlist_path=ALLOWLIST_PATH,
        git_snapshot=_snapshot(
            tracked if tracked is not None else set(files),
            dirty=dirty,
        ),
    )


def _rewrite_archive(
    source: Path,
    destination: Path,
    replacements: dict[str, bytes],
) -> None:
    with zipfile.ZipFile(source, "r") as original:
        members = [(info.filename, original.read(info.filename)) for info in original.infolist()]
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as changed:
        for name, data in members:
            changed.writestr(exporter._zip_info(name), replacements.get(name, data))


def test_archive_contains_only_allowlisted_files_and_manifest(tmp_path: Path) -> None:
    files = {
        "README.md": "public documentation\n",
        "state/CURRENT_TASK.md": "reviewed training state\n",
        "unlisted.md": "must not be exported\n",
    }
    plan = _prepare(
        tmp_path,
        files,
        allowlisted=["README.md", "state/CURRENT_TASK.md"],
        dirty=False,
    )

    with pytest.raises(ExportError, match="acknowledge-review"):
        create_archive(plan, repo_root=tmp_path, output_path="dist/handoff.zip")

    assert not (tmp_path / "dist").exists()

    output = create_archive(
        plan,
        repo_root=tmp_path,
        output_path="dist/handoff.zip",
        acknowledge_review=True,
    )
    manifest = verify_archive(output)

    assert manifest["git_sha"] == TEST_GIT_SHA
    assert manifest["dirty"] is False
    assert [entry["path"] for entry in manifest["files"]] == [
        "README.md",
        "state/CURRENT_TASK.md",
    ]
    assert str(tmp_path) not in json.dumps(manifest)

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == [
            "README.md",
            "state/CURRENT_TASK.md",
            "MANIFEST.json",
        ]
        assert archive.read("README.md") == b"public documentation\n"
        assert "unlisted.md" not in archive.namelist()
        assert archive.comment == b""


@pytest.mark.parametrize("root_name", ["state", "reviews", "progress", "notes"])
def test_personal_record_roots_require_acknowledgement_to_write(
    tmp_path: Path,
    root_name: str,
) -> None:
    relative = f"{root_name}/record.md"
    plan = _prepare(tmp_path, {relative: "reviewed text\n"})

    with pytest.raises(ExportError, match="acknowledge-review"):
        create_archive(plan, repo_root=tmp_path, output_path="dist/handoff.zip")

    assert not (tmp_path / "dist").exists()


def test_dry_run_does_not_create_dist_or_require_acknowledgement(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    files = {"state/CURRENT_TASK.md": "review me\n"}
    _write_files(tmp_path, files)
    _write_allowlist(tmp_path, list(files))

    exit_code = main(
        ["--dry-run", "--allowlist", ALLOWLIST_PATH],
        repo_root=tmp_path,
        git_snapshot=_snapshot(set(files)),
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Dry run" in output
    assert "Review acknowledgement required to write: true" in output
    assert str(tmp_path) not in output
    assert not (tmp_path / "dist").exists()


def test_verify_cli_does_not_extract_or_disclose_absolute_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = _prepare(tmp_path, {"README.md": "hello\n"})
    create_archive(plan, repo_root=tmp_path, output_path="dist/handoff.zip")

    exit_code = main(["--verify", "dist/handoff.zip"], repo_root=tmp_path)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Verified: dist/handoff.zip" in output
    assert str(tmp_path) not in output
    assert not (tmp_path / "README.md").is_dir()


def test_allowlisted_file_must_be_tracked(tmp_path: Path) -> None:
    _write_files(tmp_path, {"README.md": "hello\n", "OTHER.md": "tracked\n"})
    _write_allowlist(tmp_path, ["README.md"])

    with pytest.raises(ExportError, match="not tracked"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"OTHER.md"}),
        )


def test_explicit_empty_tracked_set_is_not_replaced(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="tracked paths"):
        _prepare(tmp_path, {"README.md": "hello\n"}, tracked=set())


def test_real_git_snapshot_supports_clean_and_dirty_content(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {
            "README.md": "committed\n",
            ALLOWLIST_PATH: json.dumps(
                {"schema_version": 1, "files": ["README.md"]}
            )
            + "\n",
        },
    )
    subprocess.run(["git", "-C", str(tmp_path), "init", "-b", "main"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Export Test"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "config",
            "user.email",
            "export-test@example.invalid",
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "add", "--all"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "fixture"],
        check=True,
        stdout=subprocess.PIPE,
    )

    clean = prepare_export(repo_root=tmp_path, allowlist_path=ALLOWLIST_PATH)
    assert clean.dirty is False
    assert clean.files[0].data == b"committed\n"

    (tmp_path / "README.md").write_bytes(b"working tree\n")
    dirty = prepare_export(repo_root=tmp_path, allowlist_path=ALLOWLIST_PATH)
    assert dirty.dirty is True
    assert dirty.files[0].data == b"working tree\n"


def test_missing_allowlisted_file_fails_closed(tmp_path: Path) -> None:
    _write_allowlist(tmp_path, ["missing.md"])

    with pytest.raises(ExportError, match="missing"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"missing.md"}),
        )


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.md",
        "/absolute.md",
        "C:/Users/example/file.md",
        "nested\\file.md",
        "nested//file.md",
        "nested/./file.md",
        "MANIFEST.json",
        "trailing.md ",
        "bad?.md",
    ],
)
def test_unsafe_allowlist_paths_are_rejected(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    _write_allowlist(tmp_path, [unsafe_path])

    with pytest.raises(ExportError):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({unsafe_path}),
        )


def test_casefold_collisions_are_rejected_before_file_access(tmp_path: Path) -> None:
    _write_allowlist(tmp_path, ["Report.md", "report.md"])

    with pytest.raises(ExportError, match="collide"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"Report.md", "report.md"}),
        )


@pytest.mark.parametrize(
    "content",
    [
        b"not-utf8: \xff\xfe",
        b"contains\x00nul",
        "hidden\u202esequence".encode("utf-8"),
        b"control\x01character",
    ],
)
def test_only_plain_utf8_text_is_allowed(tmp_path: Path, content: bytes) -> None:
    with pytest.raises(ExportError):
        _prepare(tmp_path, {"README.md": content})


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "config/.env.production",
        "credentials.json",
        "id_rsa",
        "artifact.pem",
        "notebook.ipynb",
        "image.png",
    ],
)
def test_sensitive_or_non_text_filenames_are_rejected(
    tmp_path: Path,
    path: str,
) -> None:
    with pytest.raises(ExportError):
        _prepare(tmp_path, {path: "synthetic content\n"})


@pytest.mark.parametrize(
    "secret",
    [
        "-----BEGIN " + "PRIVATE KEY-----\n",
        "gh" + "p_" + "A" * 30,
        "sk-" + "B" * 30,
        "hf_" + "C" * 30,
        "AKIA" + "C" * 16,
        "api_key = " + "D" * 24,
        "WANDB_API_KEY=" + "E" * 32,
        '"access_token": "' + "F" * 24 + '"',
        "https://user:password@example.invalid/resource",
        "C:\\Users\\RealName\\private.txt",
        "/home/realname/private.txt",
    ],
)
def test_likely_secrets_and_user_paths_are_rejected(
    tmp_path: Path,
    secret: str,
) -> None:
    with pytest.raises(ExportError, match="possible"):
        _prepare(tmp_path, {"README.md": secret})


def test_file_and_total_size_limits_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exporter, "MAX_FILE_BYTES", 4)
    with pytest.raises(ExportError, match="size limit"):
        _prepare(tmp_path, {"README.md": "12345"})

    monkeypatch.setattr(exporter, "MAX_FILE_BYTES", 10)
    monkeypatch.setattr(exporter, "MAX_TOTAL_BYTES", 5)
    with pytest.raises(ExportError, match="total size"):
        _prepare(tmp_path, {"a.md": "123", "b.md": "456"})


def test_verify_enforces_total_member_size_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = _prepare(tmp_path, {"a.md": "123", "b.md": "456"})
    archive = create_archive(
        plan,
        repo_root=tmp_path,
        output_path="dist/handoff.zip",
    )
    monkeypatch.setattr(exporter, "MAX_TOTAL_BYTES", 5)

    with pytest.raises(ExportError, match="total size"):
        verify_archive(archive)


def test_allowlist_file_count_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exporter, "MAX_FILES", 1)
    _write_allowlist(tmp_path, ["a.md", "b.md"])

    with pytest.raises(ExportError, match="file limit"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"a.md", "b.md"}),
        )


def test_file_symlink_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    link = tmp_path / "linked.md"
    try:
        os.symlink(outside, link)
    except (NotImplementedError, OSError):
        pytest.skip("symlink creation unavailable on this platform")
    _write_allowlist(tmp_path, ["linked.md"])

    with pytest.raises(ExportError, match="links and reparse"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"linked.md"}),
        )


def test_symlinked_parent_directory_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-dir"
    outside.mkdir()
    (outside / "file.md").write_text("outside\n", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("directory symlink creation unavailable on this platform")
    _write_allowlist(tmp_path, ["linked/file.md"])

    with pytest.raises(ExportError, match="links and reparse"):
        prepare_export(
            repo_root=tmp_path,
            allowlist_path=ALLOWLIST_PATH,
            git_snapshot=_snapshot({"linked/file.md"}),
        )


def test_windows_reparse_attribute_is_recognized() -> None:
    fake_stat = SimpleNamespace(
        st_mode=stat.S_IFREG,
        st_file_attributes=0x400,
    )

    assert exporter._is_link_or_reparse(fake_stat)


def test_prepared_bytes_are_used_even_if_source_changes(tmp_path: Path) -> None:
    plan = _prepare(tmp_path, {"README.md": "before\n"})
    (tmp_path / "README.md").write_text("after\n", encoding="utf-8")

    output = create_archive(plan, repo_root=tmp_path, output_path="dist/handoff.zip")

    with zipfile.ZipFile(output) as archive:
        assert archive.read("README.md") == b"before\n"


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    plan = _prepare(tmp_path, {"README.md": "hello\n"})
    output = tmp_path / "dist" / "handoff.zip"
    output.parent.mkdir()
    output.write_bytes(b"keep me")

    with pytest.raises(ExportError, match="refusing to overwrite"):
        create_archive(plan, repo_root=tmp_path, output_path="dist/handoff.zip")

    assert output.read_bytes() == b"keep me"


def test_verify_rejects_payload_that_does_not_match_manifest(tmp_path: Path) -> None:
    plan = _prepare(tmp_path, {"README.md": "original\n"})
    original = create_archive(plan, repo_root=tmp_path, output_path="dist/original.zip")
    tampered = tmp_path / "dist" / "tampered.zip"
    _rewrite_archive(original, tampered, {"README.md": b"tampered\n"})

    with pytest.raises(ExportError, match="size|hash"):
        verify_archive(tampered)


def test_verify_rejects_path_traversal_member(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    minimal_manifest = {
        "schema_version": 1,
        "git_sha": TEST_GIT_SHA,
        "dirty": False,
        "files": [],
    }
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr("../outside.md", "unsafe")
        archive.writestr("MANIFEST.json", json.dumps(minimal_manifest))

    with pytest.raises(ExportError):
        verify_archive(archive_path)


def test_verify_rejects_duplicate_archive_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "duplicates.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr("README.md", "first")
            archive.writestr("README.md", "second")
            archive.writestr("MANIFEST.json", "{}")

    with pytest.raises(ExportError, match="duplicate"):
        verify_archive(archive_path)


def test_manifest_hash_and_size_match_exact_source_bytes(tmp_path: Path) -> None:
    source = "你好, handoff\n".encode("utf-8")
    plan = _prepare(tmp_path, {"README.md": source})

    entry = plan.manifest()["files"][0]

    assert entry == {
        "path": "README.md",
        "size": len(source),
        "sha256": hashlib.sha256(source).hexdigest(),
    }
