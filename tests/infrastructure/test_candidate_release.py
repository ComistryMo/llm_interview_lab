"""Release/version/public upgrade checks, with entirely synthetic data."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from llm_interview_lab import __version__
from llm_interview_lab.desktop import runtime
from llm_interview_lab.release_version import release_metadata, version_key

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_build_checks", ROOT / "scripts/release_metadata.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_source_tag_notes_and_bundle_versions_are_consistent():
    metadata = release.check_source(ROOT)
    assert metadata["version"] == __version__
    assert version_key(metadata["tag"]) == version_key(__version__)
    assert release_metadata("1.2.3rc2")["bundle_version"] == "2.2.3fc2"
    assert release_metadata("1.2.3")["bundle_version"] == "2.2.3"
    with pytest.raises(RuntimeError, match="tag"):
        release.check_source(ROOT, "v0.0.0")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    publish = ci.split("  publish-release:")[1]
    assert "inputs.publish == true" in publish and "refs/tags/v" in publish
    assert "--verify-tag" in publish and "--clobber" not in ci
    for job in ("repository-health", "cpu-pytorch-validation", "documentation", "desktop-windows", "desktop-macos-arm64"):
        assert f"      - {job}" in publish


def test_macos_candidate_minimum_matches_actual_runtime_wheels():
    # Qt's wheel requires 13, but the installed NumPy/SciPy Accelerate wheels
    # require 14. The declaration must cover the complete bundled runtime.
    build = (ROOT / "scripts/build_macos_desktop.py").read_text("utf-8")
    checker = (ROOT / "scripts/check_macos_artifact.py").read_text("utf-8")
    spec = (ROOT / "scripts/pysidedeploy-macos.spec").read_text("utf-8")
    assert 'MINIMUM_MACOS = "14.0"' in build
    assert '"LSMinimumSystemVersion": "14.0"' in checker
    assert "--macos-app-macos-min-version=14.0" in spec


def test_release_assembly_verifies_producer_hashes_and_duplicates(tmp_path):
    downloads = tmp_path / "downloads"
    for platform, names, sums in (("windows", release.ASSETS[:1], "SHA256SUMS-Windows.txt"), ("macos", release.ASSETS[1:], "SHA256SUMS.txt")):
        directory = downloads / platform
        directory.mkdir(parents=True)
        lines = []
        for name in names:
            path = directory / name
            path.write_bytes(b"synthetic artifact " + name.encode())
            lines.append(f"{release.sha256(path)}  {name}\n")
        (directory / sums).write_text("".join(lines), encoding="utf-8")
    output = tmp_path / "verified"
    release.assemble(downloads, output)
    assert len((output / "SHA256SUMS.txt").read_text().splitlines()) == 3
    with pytest.raises(FileExistsError):
        release.assemble(downloads, output)
    altered = downloads / "macos" / release.ASSETS[1]
    altered.write_bytes(b"changed since producer verification")
    with pytest.raises(RuntimeError, match="checksum"):
        release.assemble(downloads, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
    shutil.copy2(downloads / "windows" / release.ASSETS[0], downloads / release.ASSETS[0])
    with pytest.raises(RuntimeError, match="exactly one"):
        release.assemble(downloads, tmp_path / "duplicate")


def test_interrupted_public_upgrade_retries_without_private_changes(tmp_path, monkeypatch):
    destination = tmp_path / "候选 升级 数据"
    monkeypatch.setenv("LLM_LAB_PACKAGED", "1")
    monkeypatch.setenv("LLM_LAB_BUNDLE_ROOT", str(ROOT))
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(destination))
    runtime.prepare_desktop_repository()
    # Only explicitly created synthetic sentinels, not any real workspace.
    sentinels = ["workspace/profiles/synthetic/profile.yaml", "workspace/profiles/synthetic/events.jsonl",
                 "workspace/profiles/synthetic/interview_drafts/session/q-001.json",
                 "workspace/profiles/synthetic/materials/resume.txt", "settings.ini", "models/weights.bin"]
    for name in sentinels:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic untouched data:" + name.encode())
    before = {name: (destination / name).read_bytes() for name in sentinels}
    marker = destination / runtime.STANDALONE_MARKER
    old = json.loads(marker.read_text())
    old["version"] = "0.4.0a3"
    marker.write_text(json.dumps(old), encoding="utf-8")
    old_bytes = marker.read_bytes()
    copytree = runtime.shutil.copytree
    def interrupted(source, target, *args, **kwargs):
        if Path(source) == ROOT / "coach":
            raise OSError("synthetic interrupted public copy")
        return copytree(source, target, *args, **kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(runtime.shutil, "copytree", interrupted)
        with pytest.raises(OSError, match="interrupted"):
            runtime.prepare_desktop_repository()
    assert marker.read_bytes() == old_bytes
    runtime.prepare_desktop_repository()
    assert json.loads(marker.read_text())["version"] == __version__
    for prefix in ("curriculum", "coach", "workspace/schema", "workspace/templates"):
        for source in (ROOT / prefix).rglob("*"):
            if source.is_file():
                assert (destination / source.relative_to(ROOT)).read_bytes() == source.read_bytes()
    # Packaged same-version relaunch does not re-copy or touch private data.
    monkeypatch.setattr(runtime, "_copy_public_assets", lambda *args: pytest.fail("copied on unchanged relaunch"))
    assert runtime.prepare_desktop_repository() == destination.resolve()
    assert {name: (destination / name).read_bytes() for name in sentinels} == before
