from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

import pytest


pytestmark = [pytest.mark.infrastructure]

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
TEXT_SUFFIXES = {".md", ".py", ".toml", ".txt", ".json", ".jsonl", ".yml", ".yaml"}


def _repository_candidate_names() -> list[str]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        names = [name for name in result.stdout.decode("utf-8").split("\x00") if name]
    except UnicodeDecodeError as error:
        raise AssertionError("Git returned a non-UTF-8 tracked path") from error
    assert names, "repository contract requires tracked files"
    return names


def _repository_candidate_files() -> list[Path]:
    files: list[Path] = []
    for name in _repository_candidate_names():
        path = REPO_ROOT.joinpath(*name.split("/"))
        file_stat = os.lstat(path)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attributes = getattr(file_stat, "st_file_attributes", 0)
        assert not stat.S_ISLNK(file_stat.st_mode), f"repository symlink: {name}"
        assert not attributes & reparse_flag, f"repository reparse path: {name}"
        assert stat.S_ISREG(file_stat.st_mode), f"repository non-file: {name}"
        files.append(path)
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
        "docs/CURRICULUM_METADATA.md",
        "docs/STATE_MODEL.md",
        "docs/PRIVACY_AND_SECURITY.md",
        "docs/REFERENCE_POLICY.md",
        "docs/EXTERNAL_COURSE_PACKS.md",
        "docs/AI_COACH_ADAPTER.md",
        "docs/CUSTOMIZATION.md",
        "curriculum/schema/catalog.schema.json",
        "curriculum/catalog/foundation.yaml",
        "curriculum/problems/FND-001-wrong-prediction-count/task.md",
        "curriculum/problems/FND-001-wrong-prediction-count/starter.py",
        "curriculum/problems/FND-001-wrong-prediction-count/test_public.py",
        "curriculum/problems/FND-001-wrong-prediction-count/hints.md",
        "curriculum/catalog.json",
        "curriculum/NAVIGATION.md",
        "curriculum/external/catalog.json",
        "curriculum/external/NAVIGATION.md",
        "curriculum/external/stanford_cs336/manifest.json",
        "references/registry.json",
        "scripts/validate_curriculum.py",
        "scripts/validate_external_courses.py",
        "scripts/manage_external_course.py",
        "scripts/run_current_task.py",
        "scripts/select_current_task.py",
        "scripts/create_private_workspace.py",
        "src/llm_interview_lab/cli.py",
        "src/llm_interview_lab/catalog.py",
        "src/llm_interview_lab/dag.py",
        "src/llm_interview_lab/events.py",
        "src/llm_interview_lab/grader.py",
        "src/llm_interview_lab/pytest_plugin.py",
        "src/llm_interview_lab/submissions.py",
        "src/llm_interview_lab/workspace.py",
        "templates/starter/src/stage00/hard_sample_miner.py",
        "workspace/README.md",
        "workspace/schema/profile.schema.json",
        "workspace/schema/event.schema.json",
        "workspace/templates/default/profile.yaml",
        "workspace/demo/profile.yaml",
        "workspace/demo/events.jsonl",
        "workspace/profiles/.gitkeep",
    }

    missing = sorted(path for path in required if not (REPO_ROOT / path).is_file())
    assert not missing, f"missing authoritative documents: {missing}"


def test_external_checkout_root_has_no_tracked_files() -> None:
    tracked_external = sorted(
        name
        for name in _repository_candidate_names()
        if ".external" in PurePosixPath(name).parts
    )

    assert not tracked_external, (
        "external course checkouts must remain untracked:\n" + "\n".join(tracked_external)
    )


def test_transient_external_and_state_lock_paths_are_ignored() -> None:
    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".external/" in ignore
    assert "/state/.task-selection.lock" in ignore
    assert "/workspace/profiles/*" in ignore
    assert "!/workspace/profiles/.gitkeep" in ignore


def test_only_workspace_profile_placeholder_is_public() -> None:
    profile_files = sorted(
        name
        for name in _repository_candidate_names()
        if name.startswith("workspace/profiles/")
    )

    assert profile_files == ["workspace/profiles/.gitkeep"]


def test_fnd001_problem_directory_has_exact_public_assets() -> None:
    prefix = "curriculum/problems/FND-001-wrong-prediction-count/"
    problem_files = {
        name.removeprefix(prefix)
        for name in _repository_candidate_names()
        if name.startswith(prefix)
    }

    assert problem_files == {"task.md", "starter.py", "test_public.py", "hints.md"}
    assert all("solution" not in name.lower() for name in problem_files)


def test_relative_markdown_links_resolve_with_exact_case() -> None:
    failures: list[str] = []
    for document in _repository_candidate_files():
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
    for path in _repository_candidate_files():
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
    assert "llm-lab init --profile default" in readme
    assert "llm-lab doctor" in readme
    assert "llm-lab next --profile default" in readme
    assert 'requires-python = ">=3.10"' in pyproject
    assert 'license = "Apache-2.0"' in pyproject


def test_pytest_collection_boundary_is_explicit() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'testpaths = ["tests/infrastructure", "tests/regression"]' in pyproject
    assert '"curriculum/problems"' in pyproject
    assert '"workspace/profiles"' in pyproject


def test_external_task_selection_language_is_unambiguous() -> None:
    curriculum_readme = (REPO_ROOT / "curriculum" / "README.md").read_text(
        encoding="utf-8"
    )
    external_guide = (REPO_ROOT / "docs" / "EXTERNAL_COURSE_PACKS.md").read_text(
        encoding="utf-8"
    )
    generated_navigation = (
        REPO_ROOT / "curriculum" / "external" / "NAVIGATION.md"
    ).read_text(encoding="utf-8")

    assert "安装和 Preview 不自动进入状态机" in curriculum_readme
    assert "scripts/select_current_task.py" in external_guide
    assert "learner ledger 中 canonical task 的状态**只描述 companion runtime**" in external_guide
    assert "安装与 Preview 不会改变 `state/CURRENT_TASK.md`" in generated_navigation
    assert "只有 assignment 升级为 `implementation-ready` 后" in generated_navigation
    assert "当前 `inventory-audited` 项目 fail closed" in generated_navigation


def test_removed_duplicate_reports_do_not_return() -> None:
    forbidden_names = {
        "CODEX_TRAINING_REPORT.md",
    }
    names = {path.name for path in _repository_candidate_files()}
    assert names.isdisjoint(forbidden_names)
