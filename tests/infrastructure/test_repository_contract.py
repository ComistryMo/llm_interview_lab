from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess

import pytest

import llm_interview_lab
from llm_interview_lab.catalog import PROBLEM_ASSETS, RETENTION_ASSETS, load_catalog


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def test_package_version_matches_pyproject() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', pyproject)
    assert match is not None
    assert llm_interview_lab.__version__ == match.group(1)


def _assert_exact_case(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT)
    current = REPO_ROOT
    for part in relative.parts:
        assert part in {child.name for child in current.iterdir()}, (
            f"link casing does not match the tracked path: {relative.as_posix()}"
        )
        current = current / part


def test_public_entrypoints_and_maintained_docs_exist() -> None:
    required = {
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "AGENTS.md",
        "pyproject.toml",
        "docs/architecture.md",
        "docs/workspace.md",
        "docs/curriculum-authoring.md",
        "coach/POLICY.md",
        "coach/prompts/reviewer.md",
        "coach/prompts/teacher.md",
        "coach/prompts/generate_variant.md",
        "workspace/schema/event.schema.json",
        "workspace/schema/profile.schema.json",
        "workspace/templates/default/profile.yaml",
        "workspace/demo/profile.yaml",
        "workspace/demo/events.jsonl",
    }

    missing = sorted(path for path in required if not (REPO_ROOT / path).is_file())
    assert not missing, f"missing maintained public files: {missing}"


def test_catalog_has_mvp_scale_and_only_ready_nodes_have_asset_directories() -> None:
    catalog = load_catalog(REPO_ROOT)
    ready = [problem for problem in catalog.problems.values() if problem.ready]
    planned = [problem for problem in catalog.problems.values() if not problem.ready]

    assert len(ready) >= 32
    assert len(planned) >= 100
    assert len(catalog.tracks) >= 12
    assert len(catalog.quests) >= 10
    assert len(catalog.capstones) >= 8
    assert all(problem.problem_dir is None for problem in planned)
    assert len(list((REPO_ROOT / "curriculum/problems").iterdir())) == len(ready)


@pytest.mark.parametrize(
    "problem_id",
    sorted(
        problem.id
        for problem in load_catalog(REPO_ROOT).problems.values()
        if problem.ready
    ),
)
def test_ready_problem_assets_are_answer_free_and_use_the_shared_loader(
    problem_id: str,
) -> None:
    problem = load_catalog(REPO_ROOT).get(problem_id)
    assert problem.problem_dir is not None
    assert {path.name for path in problem.problem_dir.iterdir()} == PROBLEM_ASSETS

    starter = (problem.problem_dir / "starter.py").read_text(encoding="utf-8")
    tests = (problem.problem_dir / "test_public.py").read_text(encoding="utf-8")
    tree = ast.parse(tests)
    test_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]

    assert "NotImplementedError" in starter
    assert len(test_functions) >= 5
    assert "submission" in tests
    assert "import starter" not in tests
    assert "sys.path" not in tests
    assert "load_submission" not in tests
    assert "workspace/profiles" not in tests.replace("\\", "/")
    assert problem.runner_kind == "pytest"
    assert problem.oracle_kind in {
        "fixture_expected",
        "closed_form",
        "framework_reference",
        "brute_force",
        "cross_implementation",
        "property_only",
    }
    assert len(problem.raw["assessment"]["oral_questions"]) >= 4
    assert problem.raw["variant_axes"]
    assert problem.raw["invariants"]
    assert problem.raw["common_bugs"]
    assert set(problem.raw["retention"]) == {"d2", "d7"}
    validation = problem.raw["validation"]
    assert validation["level"] in {"contract", "oracle", "field", "stable"}
    assert type(validation["field_runs"]) is int and validation["field_runs"] >= 0


def test_verified_retention_assets_are_complete_and_separate() -> None:
    catalog = load_catalog(REPO_ROOT)
    verified = []
    for problem in catalog.problems.values():
        if not problem.ready:
            continue
        for stage in ("d2", "d7"):
            variant = problem.retention_variant(REPO_ROOT, stage)
            if variant is None:
                continue
            starter, public_tests, symbol = variant
            verified.append((problem.id, stage))
            assert starter.parent == public_tests.parent
            assert {
                path.name
                for path in starter.parent.iterdir()
                if path.name != "__pycache__" and path.suffix != ".pyc"
            } == RETENTION_ASSETS
            assert starter != problem.problem_dir / "starter.py"
            assert public_tests != problem.public_tests
            assert "NotImplementedError" in starter.read_text(encoding="utf-8")
            tests = public_tests.read_text(encoding="utf-8")
            assert "submission" in tests and symbol in tests
    assert len(verified) >= 8


def test_root_pytest_collection_excludes_learning_code() -> None:
    config = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'testpaths = ["tests/infrastructure", "tests/regression"]' in config
    assert 'norecursedirs = [".external", "curriculum/problems", "curriculum/retention", "workspace/profiles"]' in config


def test_real_workspace_profiles_are_not_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--", "workspace/profiles"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tracked = [line for line in result.stdout.splitlines() if line]

    assert tracked in ([], ["workspace/profiles/.gitkeep"])


def test_obsolete_duplicate_sources_of_truth_are_absent() -> None:
    obsolete = {
        "curriculum/catalog.json",
        "curriculum/NAVIGATION.md",
        "state/CURRENT_TASK.md",
        "state/PROGRESS.md",
        "state/MISTAKE_LOG.md",
        "scripts/select_current_task.py",
        "scripts/state_model.py",
        "scripts/validate_curriculum.py",
        "docs/STATE_MODEL.md",
        "docs/CURRICULUM_METADATA.md",
    }

    remaining = sorted(path for path in obsolete if (REPO_ROOT / path).exists())
    assert not remaining, f"obsolete facts remain: {remaining}"


@pytest.mark.parametrize(
    "document",
    [
        "README.md",
        "CONTRIBUTING.md",
        "docs/architecture.md",
        "docs/workspace.md",
        "docs/curriculum-authoring.md",
        "docs/EXTERNAL_COURSE_PACKS.md",
        "references/README.md",
        "curriculum/external/README.md",
    ],
)
def test_maintained_markdown_links_resolve_with_exact_case(document: str) -> None:
    source = REPO_ROOT / document
    for raw_target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
        target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        relative = target.split("#", 1)[0]
        if not relative:
            continue
        resolved = (source.parent / relative).resolve()
        assert resolved.exists(), f"broken link in {document}: {target}"
        _assert_exact_case(resolved)
