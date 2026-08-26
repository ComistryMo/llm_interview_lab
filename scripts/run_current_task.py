"""Run the validated native current task without executing Markdown commands.

External-course tasks are detected but never executed automatically: their
third-party setup and test commands require explicit user review.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.state_model import StateValidationError  # noqa: E402
from scripts.validate_curriculum import (  # noqa: E402
    CurriculumValidationError,
    REPO_ROOT,
    validate_repository,
)
from scripts.validate_external_courses import validate_external_courses  # noqa: E402
from scripts.validate_state import validate_repository_state  # noqa: E402


@dataclass(frozen=True)
class CurrentTaskCommand:
    task_id: str
    kind: str
    pytest_nodes: tuple[str, ...] = ()
    external_assignment_id: str | None = None
    task_card: str | None = None
    completion_role: str | None = None
    companion_runtime: str | None = None
    official_runtime: str | None = None
    problem_ids: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    related_commands: tuple[Mapping[str, Any], ...] = ()
    integration_status: str | None = None
    group_prerequisites: tuple[str, ...] = ()


def resolve_task(
    task_id: str,
    *,
    native_catalog: Mapping[str, Any],
    external_manifests: Sequence[Mapping[str, Any]] = (),
) -> CurrentTaskCommand:
    """Resolve one ID using validated machine metadata only."""

    for task in native_catalog["tasks"]:
        if task["id"] == task_id:
            return CurrentTaskCommand(
                task_id=task_id,
                kind="native",
                pytest_nodes=tuple(task["test_nodes"]),
            )

    for manifest in external_manifests:
        for assignment in manifest["assignments"]:
            for group in assignment["problem_groups"]:
                canonical_id = f"{assignment['id']}-{group['id']}"
                if canonical_id == task_id:
                    command_ids = {
                        evidence.split(":", 1)[1]
                        for evidence in group["evidence"]
                        if evidence.startswith("test-command:")
                    }
                    return CurrentTaskCommand(
                        task_id=task_id,
                        kind="external",
                        external_assignment_id=assignment["id"],
                        task_card=assignment["task_card"],
                        completion_role=group["completion_role"],
                        companion_runtime=group["runtime_tier"],
                        official_runtime=group["official_runtime_tier"],
                        problem_ids=tuple(group["problem_ids"]),
                        capabilities=tuple(group["capabilities"]),
                        evidence=tuple(group["evidence"]),
                        related_commands=tuple(
                            command
                            for command in assignment["test_commands"]
                            if command["id"] in command_ids
                        ),
                        integration_status=assignment["integration_status"],
                        group_prerequisites=tuple(
                            f"{assignment['id']}-{group_id}"
                            for group_id in group["prerequisite_group_ids"]
                        ),
                    )

    raise CurriculumValidationError(
        f"current task {task_id!r} is absent from native and external validated catalogs"
    )


def native_pytest_arguments(command: CurrentTaskCommand) -> list[str]:
    if command.kind != "native" or not command.pytest_nodes:
        raise CurriculumValidationError("only native tasks with test nodes can run automatically")
    return [sys.executable, "-m", "pytest", *command.pytest_nodes, "-q"]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected native pytest nodes without running them",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        _, _, snapshot = validate_repository_state(
            repo_root=repo_root,
            ledger_path=repo_root / "state" / "TASK_LEDGER.jsonl",
            current_task_path=repo_root / "state" / "CURRENT_TASK.md",
        )
        native_catalog, _, _ = validate_repository(repo_root=repo_root)

        native_ids = {task["id"] for task in native_catalog["tasks"]}
        external_manifests: Sequence[Mapping[str, Any]] = ()
        if snapshot.task_id not in native_ids:
            _, external_manifests, _ = validate_external_courses(repo_root=repo_root)
        command = resolve_task(
            snapshot.task_id,
            native_catalog=native_catalog,
            external_manifests=external_manifests,
        )
    except (CurriculumValidationError, StateValidationError) as error:
        print(f"CURRENT TASK INVALID: {error}", file=sys.stderr)
        return 1

    if command.kind == "external":
        print(
            f"Current task {command.task_id} belongs to {command.external_assignment_id}."
        )
        print(f"Task Card: {command.task_card}")
        print(
            f"Scope: role={command.completion_role}, "
            f"companion-runtime={command.companion_runtime}, "
            f"official-runtime={command.official_runtime}"
        )
        print("Problem-group prerequisites:")
        if command.group_prerequisites:
            for prerequisite in command.group_prerequisites:
                print(f"  {prerequisite} (requires reviewed)")
        else:
            print("  none")
        print("Problems:")
        for problem_id in command.problem_ids:
            print(f"  {problem_id}")
        print("Capabilities:")
        for capability in command.capabilities:
            print(f"  {capability}")
        print("Required evidence:")
        for evidence in command.evidence:
            print(f"  {evidence}")
        print("Relevant upstream commands (review and run yourself):")
        if command.related_commands:
            for item in command.related_commands:
                print(
                    f"  [{item['id']} | {item['scope']} | {item['runtime_tier']}] "
                    f"{item['command']}"
                )
        else:
            print("  none; use the artifact/oral evidence contract above")
        print(
            "Automatic execution is disabled for third-party assignments. Review the Task Card, "
            f"then run `python scripts/manage_external_course.py show-group {command.task_id}` "
            "for the same scoped contract."
        )
        return 2

    arguments = native_pytest_arguments(command)
    print(f"Current native task: {command.task_id}")
    print("Pytest nodes:")
    for node in command.pytest_nodes:
        print(f"  {node}")
    if args.dry_run:
        return 0
    try:
        return subprocess.run(arguments, cwd=repo_root, check=False).returncode
    except OSError as error:
        print(
            f"CURRENT TASK ERROR: pytest could not be started ({type(error).__name__})",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
