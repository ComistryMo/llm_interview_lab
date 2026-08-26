from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import subprocess

import pytest


pytestmark = [pytest.mark.infrastructure]

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".json", ".jsonl", ".yml", ".yaml"}


def _tracked_candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        names = result.stdout.decode("utf-8").split("\x00")
    except UnicodeDecodeError as error:
        raise AssertionError("Git returned a non-UTF-8 tracked path") from error
    files: list[Path] = []
    for name in names:
        if not name:
            continue
        path = REPO_ROOT.joinpath(*name.split("/"))
        file_stat = os.lstat(path)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attributes = getattr(file_stat, "st_file_attributes", 0)
        assert not stat.S_ISLNK(file_stat.st_mode), f"tracked symlink: {name}"
        assert not attributes & reparse_flag, f"tracked reparse path: {name}"
        assert stat.S_ISREG(file_stat.st_mode), f"tracked non-file: {name}"
        files.append(path)
    assert files, "repository contract requires tracked files"
    return files


def _has_exact_case(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT.resolve())
    current = REPO_ROOT.resolve()
    for part in relative.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current = current / part
    return True


def test_authoritative_public_documents_exist() -> None:
    required = {
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "AGENTS.md",
        "docs/GETTING_STARTED.md",
        "docs/COACHING_PROTOCOL.md",
        "docs/STATE_MODEL.md",
        "docs/PRIVACY_AND_SECURITY.md",
        "docs/AI_COACH_ADAPTER.md",
        "docs/CUSTOMIZATION.md",
        "scripts/create_private_workspace.py",
        "templates/starter/src/stage00/hard_sample_miner.py",
    }

    missing = sorted(path for path in required if not (REPO_ROOT / path).is_file())
    assert not missing, f"missing authoritative documents: {missing}"


def test_relative_markdown_links_resolve_with_exact_case() -> None:
    failures: list[str] = []
    for document in _tracked_candidate_files():
        if document.suffix.lower() != ".md":
            continue
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            clean = target.strip().split("#", 1)[0]
            if not clean or clean.startswith(("http://", "https://", "mailto:")):
                continue
            linked = (document.parent / clean).resolve()
            try:
                linked.relative_to(REPO_ROOT.resolve())
            except ValueError:
                failures.append(f"{document.relative_to(REPO_ROOT)} -> {target}: outside repo")
                continue
            if not linked.exists():
                failures.append(f"{document.relative_to(REPO_ROOT)} -> {target}: missing")
                continue
            if not _has_exact_case(linked):
                failures.append(f"{document.relative_to(REPO_ROOT)} -> {target}: case mismatch")

    assert not failures, "\n".join(failures)


def test_public_text_is_utf8_and_has_no_known_private_identifiers() -> None:
    # Build retired private identifiers from fragments so the scanner test
    # itself does not keep those identifiers in the public tree.
    forbidden = (
        "洪" + "洲",
        "蔚" + "来",
        "百" + "度",
        "Tele" + "AI",
    )
    findings: list[str] = []
    for path in _tracked_candidate_files():
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for identifier in forbidden:
            if identifier in text:
                findings.append(f"{path.relative_to(REPO_ROOT)}: {identifier}")

    assert not findings, "known private identifiers found:\n" + "\n".join(findings)


def test_readme_commands_and_metadata_are_consistent() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "python -m pytest -q" in readme
    assert "python scripts/check_environment.py" in readme
    assert "python scripts/validate_state.py" in readme
    assert 'requires-python = ">=3.10"' in pyproject
    assert 'license = "Apache-2.0"' in pyproject


def test_removed_duplicate_reports_do_not_return() -> None:
    forbidden_names = {
        "CODEX_TRAINING_REPORT.md",
    }
    names = {path.name for path in _tracked_candidate_files()}
    assert names.isdisjoint(forbidden_names)
