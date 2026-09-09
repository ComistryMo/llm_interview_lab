"""Incremental update protocol, real reconstruction and native install handoff."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
import time
import zipfile

import pytest

from llm_interview_lab.desktop import update_payload as payload
from llm_interview_lab.desktop.update_install import prepare_handoff, launch_handoff


def archive(path, entries, target="windows-x64"):
    prefix = "LLMInterviewLab.app" if target == "macos-arm64" else "LLMInterviewLab"
    with zipfile.ZipFile(path, "w") as result:
        for name, data in entries.items():
            info = zipfile.ZipInfo(prefix + "/" + name)
            if isinstance(data, tuple):
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                data = data[0].encode()
            else:
                info.external_attr = (stat.S_IFREG | 0o755) << 16
            result.writestr(info, data)
    return path


def make_feed(tmp_path, entries, target="windows-x64"):
    out = tmp_path / "payloads"
    manifest = payload.build_payload(archive(tmp_path / "release.zip", entries, target), target, "v1.0.2", out)
    calls = []
    def fetch(name, spec):
        calls.append(name)
        return (out / name).read_bytes()
    return manifest, fetch, calls


def test_rebuild_uses_unchanged_files_and_blocks_without_installer(tmp_path):
    old = tmp_path / "installed"
    old.mkdir()
    unchanged = b"a" * payload.BLOCK_SIZE
    (old / "LLMInterviewLab.exe").write_bytes(unchanged + b"old" * 400000)
    (old / "unchanged.txt").write_bytes(b"keep")
    (old / "removed.txt").write_bytes(b"obsolete")
    (old / "user-file.txt").write_bytes(b"untouched user data")
    entries = {"LLMInterviewLab.exe": unchanged + b"new" * 400000,
               "unchanged.txt": b"keep", "new/note.txt": "新功能".encode()}
    manifest, fetch, calls = make_feed(tmp_path, entries)
    result = payload.reconstruct(manifest, old, tmp_path / "next", fetch, threading.Event(), lambda n: None)
    assert result["reused_bytes"] == len(unchanged) + 4
    assert result["downloaded_bytes"] < 10000
    for name, data in entries.items():
        assert (tmp_path / "next" / name).read_bytes() == data
    assert not (tmp_path / "next/removed.txt").exists()
    assert (old / "removed.txt").read_bytes() == b"obsolete"
    assert (old / "user-file.txt").read_bytes() == b"untouched user data"
    assert all(name.startswith("update-") for name in calls)


def test_unchanged_app_requires_zero_payload_downloads(tmp_path):
    old = tmp_path / "installed"
    old.mkdir()
    entries = {"LLMInterviewLab.exe": b"x" * (payload.SMALL_FILE + 1), "title.txt": b"same"}
    for name, data in entries.items():
        (old / name).write_bytes(data)
    manifest, fetch, calls = make_feed(tmp_path, entries)
    payload.reconstruct(manifest, old, tmp_path / "next", fetch, threading.Event(), lambda n: None)
    assert calls == []


def test_corruption_and_cancel_never_modify_old_app(tmp_path):
    old = tmp_path / "installed"
    old.mkdir()
    (old / "LLMInterviewLab.exe").write_bytes(b"old")
    manifest, fetch, calls = make_feed(tmp_path, {"LLMInterviewLab.exe": b"new"})
    with pytest.raises(payload.PayloadError, match="校验"):
        payload.reconstruct(manifest, old, tmp_path / "bad", lambda *_: b"corrupted", threading.Event(), lambda n: None)
    stopped = threading.Event()
    stopped.set()
    with pytest.raises(payload.PayloadError, match="取消"):
        payload.reconstruct(manifest, old, tmp_path / "cancelled", fetch, stopped, lambda n: None)
    assert (old / "LLMInterviewLab.exe").read_bytes() == b"old" and calls == []


@pytest.mark.parametrize("name", ["../outside", "/outside", "C:/outside", "a/../../b", "a\\b"])
def test_manifest_paths_cannot_escape_staging(tmp_path, name):
    manifest, _, _ = make_feed(tmp_path, {"LLMInterviewLab.exe": b"test"})
    manifest["files"][name] = manifest["files"]["LLMInterviewLab.exe"]
    with pytest.raises(payload.PayloadError):
        payload.validate_manifest(manifest, "windows-x64", "v1.0.2")


def test_macos_internal_symlink_and_mode(tmp_path):
    manifest, fetch, _ = make_feed(tmp_path, {
        "Contents/MacOS/main": b"binary", "Contents/Framework/Versions/A/library": b"library",
        "Contents/Framework/Versions/Current": ("A",),
    }, "macos-arm64")
    if os.name == "nt":
        # Windows developer-mode symlinks are not assumed. Validation is portable.
        manifest["files"]["Contents/Framework/Versions/Current"]["link"] = "../../../../../outside"
        with pytest.raises(payload.PayloadError, match="越出"):
            payload.validate_manifest(manifest, "macos-arm64", "v1.0.2")
        return
    old = tmp_path / "installed"
    old.mkdir()
    payload.reconstruct(manifest, old, tmp_path / "next", fetch, threading.Event(), lambda n: None)
    assert (tmp_path / "next/Contents/Framework/Versions/Current/library").read_bytes() == b"library"
    assert (tmp_path / "next/Contents/MacOS/main").stat().st_mode & stat.S_IXUSR


@pytest.mark.parametrize("successful", [True, False])
def test_native_swap_restart_and_rollback_in_isolated_directory(tmp_path, successful):
    """Run the shipped OS helper against synthetic programs, never the user's app."""
    app = tmp_path / "Synthetic app"
    app.mkdir()
    (app / "old-marker").write_text("old")
    target = "windows-x64" if os.name == "nt" else "macos-arm64"
    handoff = prepare_handoff(app, target, "v1.0.2")
    next_app = Path(handoff["staging"])
    next_app.mkdir()
    (next_app / "new-marker").write_text("new")
    receipt = Path(handoff["handoff"])
    resources = Path(__file__).parents[2] / "src/llm_interview_lab/desktop/resources"
    # Synthetic entrypoints are OS scripts; production uses the verified binary.
    if os.name == "nt":
        entry = "test-app.cmd"
        ready = receipt.parent / "ready"
        (app / entry).write_text("@exit /b 0\n", encoding="ascii")
        (next_app / entry).write_text((f'@echo ready>"{ready}"\n@timeout /t 2 /nobreak >nul\n' if successful else "@exit /b 1\n"), encoding="ascii")
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(resources / "apply_update.ps1")]
    else:
        entry = "test-app.sh"
        (app / entry).write_text("#!/bin/sh\nexit 0\n")
        (next_app / entry).write_text((f'#!/bin/sh\nprintf ready > "{receipt.parent}/ready"\nsleep 2\n' if successful else "#!/bin/sh\nexit 1\n"))
        for p in (app / entry, next_app / entry): p.chmod(0o755)
        command = ["/bin/sh", str(resources / "apply_update.sh")]
    # Get a confirmed exited process ID, rather than assuming a PID is unused.
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    result = subprocess.run([*command, str(app), str(next_app), handoff["previous"], str(process.pid), str(receipt), entry],
                            capture_output=True, timeout=15)
    status = (receipt.parent / "status").read_text()
    assert status == ("installed" if successful else "rolled_back"), (result.stdout, result.stderr, status)
    assert (app / ("new-marker" if successful else "old-marker")).is_file()
    assert (receipt.parent / ("previous" if successful else "failed")).is_dir()


def test_launcher_rejects_wrong_target_before_spawning(tmp_path):
    directory = tmp_path / ".llm-update-synthetic"
    directory.mkdir()
    receipt = directory / "handoff.json"
    receipt.write_text(json.dumps({"installed": str(tmp_path), "staging": "/wrong", "previous": "/wrong"}))
    with pytest.raises(payload.PayloadError):
        launch_handoff(receipt)
