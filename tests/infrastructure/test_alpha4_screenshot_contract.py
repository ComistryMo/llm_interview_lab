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

    screenshot_inputs = (
        "src/llm_interview_lab/desktop/qml",
        "src/llm_interview_lab/desktop/resources",
        "src/llm_interview_lab/desktop/main.py",
        "src/llm_interview_lab/desktop/controller.py",
        "src/llm_interview_lab/application.py",
        "scripts/capture_desktop_screenshots.py",
    )
    changed = _git(
        "diff",
        "--name-only",
        f"{source_commit}..HEAD",
        "--",
        *screenshot_inputs,
    )
    assert changed.returncode == 0, changed.stderr
    assert not changed.stdout.strip(), (
        "checked-in screenshots are stale because screenshot-affecting files "
        "changed after source_commit:\n" + changed.stdout
    )


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
