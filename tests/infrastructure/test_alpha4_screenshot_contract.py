"""Integrity contracts for checked-in desktop screenshot evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs/images/screenshot-manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_real_asset(entry: dict, source_commit: str) -> None:
    relative = Path(entry["path"])
    assert not relative.is_absolute(), entry["path"]
    path = (REPO_ROOT / relative).resolve()
    assert path.is_relative_to(REPO_ROOT.resolve()), entry["path"]
    assert path.is_file(), entry["path"]
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", entry["path"]
    assert entry["source_commit"] == source_commit, entry["path"]
    assert entry["synthetic"] is True, entry["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], (
        entry["path"]
    )


def test_screenshot_source_commit_is_resolvable_history_evidence() -> None:
    manifest = _manifest()
    source_commit = manifest["source_commit"]
    assert isinstance(source_commit, str) and len(source_commit) == 40
    assert _git("cat-file", "-e", f"{source_commit}^{{commit}}").returncode == 0, (
        "screenshot source_commit is not available in repository history: "
        f"{source_commit}"
    )
    assert _git("merge-base", "--is-ancestor", source_commit, "HEAD").returncode == 0, (
        "screenshots must come from the current HEAD or one of its ancestors"
    )

    # This manifest is Alpha.3 historical evidence, not today's desktop.
    # Its hashes/ancestry remain mandatory; the current candidate has a
    # separate, stricter input-fingerprint contract below.


def test_v1_candidate_captures_match_their_recorded_source_and_pixels() -> None:
    from llm_interview_lab import __version__
    import struct

    path = REPO_ROOT / "docs/images/candidate-20260909/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    compatible = __version__ in [manifest["version"], *manifest.get("compatible_versions", [])]
    assert manifest["synthetic"] is True and manifest["language"] == "zh-CN"
    assert manifest["logical_size"] == [1280, 800]
    assert "production AppController" in manifest["renderer"]
    assert set(manifest["sets"]) == {"before", "after"}
    expected = {(page, theme) for page in (
        "home", "setup", "answer", "coding", "report", "connections", "settings"
    ) for theme in ("light", "dark")}
    for name, evidence in manifest["sets"].items():
        assert name in {"before", "after"}
        commit = evidence["source_commit"]
        assert _git("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
        assert {(entry["page"], entry["theme"]) for entry in evidence["screenshots"]} == expected
        assert len(evidence["screenshots"]) == len(expected)
        for entry in evidence["screenshots"]:
            asset = (REPO_ROOT / entry["path"]).resolve()
            assert asset.is_relative_to(path.parent.resolve())
            raw = asset.read_bytes()
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
            assert list(struct.unpack(">II", raw[16:24])) == entry["pixel_size"]
        inputs = evidence["source_inputs"]
        assert "src/llm_interview_lab/desktop/controller.py" in inputs
        assert "src/llm_interview_lab/application.py" in inputs
        for relative, digest in inputs.items():
            original = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO_ROOT)
            assert hashlib.sha256(original).hexdigest() == digest
            if name == "after" and compatible:
                # Compare bytes, including uncommitted changes; never stamp
                # today's SHA onto an old image to silence freshness checks.
                current_path = REPO_ROOT / relative
                current = current_path.read_bytes()
                if current_path.suffix in {".py", ".qml", ".svg", ".md", ".yaml", ".yml", ".json", ".txt", ".qrc"} or current_path.name == "qmldir":
                    current = current.replace(b"\r\n", b"\n")
                if relative == "src/llm_interview_lab/__init__.py":
                    # Preserve the capture's actual version. Only the release
                    # number may differ; all other source bytes still match.
                    current = current.replace(
                        f'__version__ = "{__version__}"'.encode(),
                        f'__version__ = "{manifest["version"]}"'.encode(),
                    )
                assert hashlib.sha256(current).hexdigest() == digest, relative
        if name == "after" and compatible:
            current_names = _git("ls-files", "--", "src/llm_interview_lab/desktop",
                                 "src/llm_interview_lab/application.py", "src/llm_interview_lab/roles.py",
                                 "src/llm_interview_lab/__init__.py", "curriculum/roles").stdout.splitlines()
            assert set(current_names) == set(inputs)


def test_connection_update_evidence_matches_source_and_pixels() -> None:
    from llm_interview_lab import __version__
    import struct

    manifest = json.loads((REPO_ROOT / "docs/images/source-alpha1/manifest.json").read_text("utf-8"))
    assert manifest["version"] == "1.0.1a1"
    assert manifest["synthetic"] is True
    assert "production AppController" in manifest["renderer"]
    commit = manifest["source_commit"]
    assert _git("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0
    assert len(manifest["screenshots"]) == 2
    for entry in manifest["screenshots"]:
        _assert_real_asset(entry, commit)
        assert list(struct.unpack(">II", (REPO_ROOT / entry["path"]).read_bytes()[16:24])) == entry["pixel_size"]
    for relative, digest in manifest["source_inputs"].items():
        original = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO_ROOT)
        assert hashlib.sha256(original).hexdigest() == digest
        if __version__ == manifest["version"]:
            assert hashlib.sha256((REPO_ROOT / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest


def test_screenshot_coverage_and_assets_match_the_manifest() -> None:
    manifest = _manifest()
    evidence = manifest["all_screenshots"]
    aliases = manifest["screenshots"]
    coverage = manifest["coverage"]

    assert coverage["count"] == len(evidence)
    assert coverage["expected_count"] == (
        len(coverage["pages"])
        * len(coverage["sizes"])
        * len(coverage["themes"])
    )
    assert coverage["expected_count"] == len(evidence)
    assert coverage["legacy_alias_count"] == len(aliases)

    paths = [entry["path"] for entry in evidence]
    assert len(paths) == len(set(paths)), "duplicate all_screenshots paths"
    combinations = {
        (entry["page"], entry["size"], entry["theme"]) for entry in evidence
    }
    expected = {
        (page, size, theme)
        for page in coverage["pages"]
        for size in coverage["sizes"]
        for theme in coverage["themes"]
    }
    assert combinations == expected

    source_commit = manifest["source_commit"]
    for entry in (*evidence, *aliases):
        _assert_real_asset(entry, source_commit)
    for alias in aliases:
        target = alias.get("alias_of")
        assert target, alias["path"]
        assert (REPO_ROOT / target).is_file(), target
