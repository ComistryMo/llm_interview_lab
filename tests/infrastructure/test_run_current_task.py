from __future__ import annotations

from pathlib import Path
import sys

import pytest

from scripts.run_current_task import (
    CurrentTaskCommand,
    main,
    native_pytest_arguments,
    resolve_task,
)
from scripts.validate_curriculum import CurriculumValidationError, load_json


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_resolve_native_task_uses_exact_catalog_nodes() -> None:
    catalog = load_json(REPO_ROOT / "curriculum" / "catalog.json")

    command = resolve_task("00A-1", native_catalog=catalog)

    assert command.kind == "native"
    assert len(command.pytest_nodes) == 6
    arguments = native_pytest_arguments(command)
    assert arguments[:3] == [sys.executable, "-m", "pytest"]
    assert arguments[-1] == "-q"
    assert arguments[3:-1] == list(command.pytest_nodes)


def test_resolve_external_group_never_returns_an_executable_command() -> None:
    catalog = load_json(REPO_ROOT / "curriculum" / "catalog.json")
    manifest = load_json(
        REPO_ROOT / "curriculum" / "external" / "stanford_cs336" / "manifest.json"
    )

    command = resolve_task(
        "EXT-CS336-A1-tokenizer-core",
        native_catalog=catalog,
        external_manifests=[manifest],
    )

    assert command.kind == "external"
    assert command.external_assignment_id == "EXT-CS336-A1"
    assert command.pytest_nodes == ()
    assert command.task_card == "curriculum/external/stanford_cs336/TASK_A1.md"
    assert command.completion_role == "portable-required"
    assert command.group_prerequisites == ()
    assert command.companion_runtime == "cpu-contract"
    assert "train_bpe" in command.problem_ids
    assert command.capabilities
    assert command.evidence
    with pytest.raises(CurriculumValidationError, match="only native tasks"):
        native_pytest_arguments(command)


def test_unknown_current_task_fails_closed() -> None:
    with pytest.raises(CurriculumValidationError, match="absent"):
        resolve_task("UNKNOWN", native_catalog={"tasks": []})


def test_repository_current_task_dry_run_is_dynamic_and_non_mutating(capsys) -> None:
    exit_code = main(["--repo-root", str(REPO_ROOT), "--dry-run"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Current native task: 00A-1" in output
    assert "tests/stage00/test_task_00a1.py::test_rejects_non_integer_prediction" in output
