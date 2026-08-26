"""Safely preview or select one validated native/external current task.

The command is dry-run by default. ``--apply`` appends a registration event
when needed and replaces only the derived CURRENT_TASK snapshot. It never edits
learner answers or executes task code.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterator, Mapping, Sequence
import uuid


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_current_task import CurrentTaskCommand, resolve_task  # noqa: E402
from scripts.state_model import (  # noqa: E402
    StateValidationError,
    TaskSnapshot,
    load_ledger,
    parse_event,
    replay_events,
)
from scripts.validate_curriculum import (  # noqa: E402
    CurriculumValidationError,
    REPO_ROOT,
    validate_repository,
)
from scripts.validate_external_courses import validate_external_courses  # noqa: E402
from scripts.validate_state import validate_repository_state  # noqa: E402


STATUS_RANK = {
    "not_started": 0,
    "attempted": 1,
    "needs_revision": 1,
    "implemented": 2,
    "reviewed": 3,
    "retained_48h": 4,
    "retained_7d": 5,
    "mastered": 6,
}


class TaskSelectionError(RuntimeError):
    """Raised when selecting a task would bypass repository training gates."""


LOCK_NAME = ".task-selection.lock"


def _is_link_or_reparse(path: Path) -> bool:
    try:
        value = os.lstat(path)
    except FileNotFoundError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & reparse_flag
    )


def _safe_state_directory(
    repo_root: Path,
    *,
    ledger_path: Path,
    current_path: Path,
) -> Path:
    """Require private state writes to remain in regular, single-link files."""

    state_dir = repo_root / "state"
    try:
        state_stat = os.lstat(state_dir)
    except FileNotFoundError as error:
        raise TaskSelectionError("state directory does not exist") from error
    if _is_link_or_reparse(state_dir) or not stat.S_ISDIR(state_stat.st_mode):
        raise TaskSelectionError("state directory must be a regular directory")
    if state_dir.resolve(strict=True) != state_dir:
        raise TaskSelectionError("state directory must resolve inside the selected repository")

    for path in (ledger_path, current_path):
        try:
            file_stat = os.lstat(path)
        except FileNotFoundError as error:
            raise TaskSelectionError(f"required state file is missing: {path.name}") from error
        if _is_link_or_reparse(path) or not stat.S_ISREG(file_stat.st_mode):
            raise TaskSelectionError(f"state file must be regular: {path.name}")
        if file_stat.st_nlink != 1:
            raise TaskSelectionError(f"state file must not be hard-linked: {path.name}")
        if path.resolve(strict=True).parent != state_dir:
            raise TaskSelectionError(f"state file escaped the state directory: {path.name}")
    return state_dir


@contextmanager
def _selection_lock(state_dir: Path) -> Iterator[None]:
    """Serialize state selection without executing platform-specific lock helpers."""

    lock_path = state_dir / LOCK_NAME
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except FileExistsError as error:
        raise TaskSelectionError(
            "task selection is already running or a stale selection lock needs inspection"
        ) from error
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _at_least(snapshot: TaskSnapshot | None, required: str) -> bool:
    return snapshot is not None and STATUS_RANK[snapshot.status.value] >= STATUS_RANK[required]


def _native_machine_gate_failures(
    task_id: str,
    *,
    catalog: Mapping[str, Any],
    snapshots: Mapping[str, TaskSnapshot],
) -> list[str]:
    task = next(task for task in catalog["tasks"] if task["id"] == task_id)
    failures: list[str] = []
    for prerequisite in task["prerequisites"]:
        prerequisite_id = prerequisite["task_id"]
        minimum = prerequisite["minimum_status"]
        if not _at_least(snapshots.get(prerequisite_id), minimum):
            actual = snapshots.get(prerequisite_id)
            actual_status = actual.status.value if actual else "not_registered"
            failures.append(f"{prerequisite_id} requires {minimum}; found {actual_status}")
    return failures


def _external_machine_gate_failures(
    assignment_id: str,
    *,
    group_prerequisites: Sequence[str],
    manifests: Sequence[Mapping[str, Any]],
    snapshots: Mapping[str, TaskSnapshot],
) -> list[str]:
    assignments = {
        assignment["id"]: assignment
        for manifest in manifests
        for assignment in manifest["assignments"]
    }
    assignment = assignments[assignment_id]
    failures: list[str] = []
    for prerequisite_id in assignment["prerequisites"]:
        prerequisite = assignments[prerequisite_id]
        required_groups = [
            group
            for group in prerequisite["problem_groups"]
            if group["completion_role"] == "portable-required"
        ]
        for group in required_groups:
            canonical_id = f"{prerequisite_id}-{group['id']}"
            if not _at_least(snapshots.get(canonical_id), "reviewed"):
                actual = snapshots.get(canonical_id)
                actual_status = actual.status.value if actual else "not_registered"
                failures.append(
                    f"{canonical_id} requires reviewed for the portable aggregate; "
                    f"found {actual_status}"
                )
    for prerequisite_id in group_prerequisites:
        if not _at_least(snapshots.get(prerequisite_id), "reviewed"):
            actual = snapshots.get(prerequisite_id)
            actual_status = actual.status.value if actual else "not_registered"
            failures.append(
                f"{prerequisite_id} requires reviewed as a problem-group prerequisite; "
                f"found {actual_status}"
            )
    return failures


def _registration_event(
    task_id: str, recorded_at: datetime, *, selection_reason: str
) -> dict[str, Any]:
    safe_id = re.sub(r"[^A-Za-z0-9]+", "-", task_id).strip("-")
    event_id = (
        f"evt-{safe_id}-registered-"
        f"{recorded_at.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    )
    return {
        "schema_version": 1,
        "event_id": event_id,
        "task_id": task_id,
        "attempt_id": None,
        "event_type": "task_registered",
        "recorded_on": None,
        "recorded_at": recorded_at.isoformat(timespec="seconds"),
        "status_before": None,
        "status_after": "not_started",
        "assistance": {"level": "H0", "demonstration_only": False},
        "variant_id": None,
        "evidence": {
            "summary": "Registered a validated task as an eligible Implementation Lane unit.",
            "artifacts": [],
            "test_result": "not_run",
            "oral_passed": None,
        },
        "reason": selection_reason,
    }


def render_current_task(command: CurrentTaskCommand, snapshot: TaskSnapshot) -> str:
    state = {
        "schema_version": 1,
        "task_id": snapshot.task_id,
        "status": snapshot.status.value,
        "latest_event_id": snapshot.latest_event_id,
        "attempt_id": snapshot.attempt_id,
        "assistance_level": snapshot.assistance_level.value,
        "demonstration_only": snapshot.demonstration_only,
        "requires_independent_variant": snapshot.requires_independent_variant,
    }
    state_json = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    if command.kind == "native":
        tests = "\n".join(f"- `{node}`" for node in command.pytest_nodes)
        detail = f"""- 类型：本项目原生任务；
- 测试节点来自受校验的 `curriculum/catalog.json`；
- 运行：`python scripts/run_current_task.py`。

## 当前范围

{tests}
"""
    else:
        problems = "\n".join(f"- `{item}`" for item in command.problem_ids)
        capabilities = "\n".join(f"- {item}" for item in command.capabilities)
        evidence = "\n".join(f"- `{item}`" for item in command.evidence)
        detail = f"""- 类型：第三方 assignment 的 canonical problem-group Task；
- 聚合 assignment：`{command.external_assignment_id}`；
- Task Card：`{command.task_card}`；
- learner 状态只证明 companion runtime `{command.companion_runtime}`；
- official runtime `{command.official_runtime}` 必须另有真实运行证据；
- 自动执行第三方命令：禁止。

## 当前 Problem

{problems}

## 当前能力目标

{capabilities}

## 当前验收证据

{evidence}

## 查看命令

`python scripts/manage_external_course.py show-group {command.task_id}`
"""
    return f"""# Current Task

<!-- CURRENT_TASK_STATE
{state_json}
END_CURRENT_TASK_STATE -->

## 当前唯一任务

- Task：`{command.task_id}`；
- 状态：`{snapshot.status.value}`；
- 当前不存在由“选择任务”产生的实现、review 或 retention 证据。

{detail}
## 开始前

确认输入、输出、边界、允许帮助与资源 Gate。一次只推进本 Task；选择不等于实现或掌握。
"""


def _write_selection(
    *,
    repo_root: Path,
    ledger_path: Path,
    current_path: Path,
    command: CurrentTaskCommand,
    snapshots: Mapping[str, TaskSnapshot],
    selection_reason: str,
) -> None:
    ledger_size_before = ledger_path.stat().st_size
    appended_line: bytes | None = None
    target_snapshot = snapshots.get(command.task_id)
    temporary = current_path.with_name(f".{current_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        if target_snapshot is None:
            recorded_at = datetime.now().astimezone()
            event_value = _registration_event(
                command.task_id,
                recorded_at,
                selection_reason=selection_reason,
            )
            parsed_event = parse_event(event_value, context="new task registration")
            current_events = load_ledger(ledger_path)
            updated_snapshots = replay_events([*current_events, parsed_event])
            target_snapshot = updated_snapshots[command.task_id]
            appended_line = (
                json.dumps(
                    event_value,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            with ledger_path.open("ab") as stream:
                stream.write(appended_line)
                stream.flush()
                os.fsync(stream.fileno())

        content = render_current_task(command, target_snapshot)
        with temporary.open("xb") as stream:
            stream.write(content.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        validate_repository_state(
            repo_root=repo_root,
            ledger_path=ledger_path,
            current_task_path=temporary,
        )
        os.replace(temporary, current_path)
    except Exception as error:
        if appended_line is not None:
            try:
                with ledger_path.open("r+b") as stream:
                    stream.seek(ledger_size_before)
                    suffix = stream.read()
                    if suffix != appended_line:
                        raise TaskSelectionError(
                            "ledger changed during selection; inspect it before retrying"
                        )
                    stream.truncate(ledger_size_before)
                    stream.flush()
                    os.fsync(stream.fileno())
            except (OSError, TaskSelectionError) as rollback_error:
                raise TaskSelectionError(
                    "task registration rollback failed; inspect the ledger before retrying"
                ) from rollback_error
        raise
    finally:
        if temporary.exists():
            temporary.unlink()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--apply", action="store_true", help="apply the previewed state change")
    parser.add_argument(
        "--acknowledge-human-gates",
        action="store_true",
        help="confirm the Task Card's non-machine-checkable readiness and resource gates",
    )
    parser.add_argument(
        "--acknowledge-paused-current",
        action="store_true",
        help="confirm that an unfinished current task will remain paused, not passed",
    )
    return parser


def _run_selection(
    *,
    args: argparse.Namespace,
    repo_root: Path,
    ledger_path: Path,
    current_path: Path,
    catalog: Mapping[str, Any],
    manifests: Sequence[Mapping[str, Any]],
    command: CurrentTaskCommand,
) -> int:
    _, _, current = validate_repository_state(
        repo_root=repo_root,
        ledger_path=ledger_path,
        current_task_path=current_path,
    )
    events = load_ledger(ledger_path)
    snapshots = replay_events(events)
    if command.kind == "native":
        machine_failures = _native_machine_gate_failures(
            command.task_id,
            catalog=catalog,
            snapshots=snapshots,
        )
    else:
        machine_failures = _external_machine_gate_failures(
            str(command.external_assignment_id),
            group_prerequisites=command.group_prerequisites,
            manifests=manifests,
            snapshots=snapshots,
        )
        if command.integration_status != "implementation-ready":
            machine_failures.insert(
                0,
                "external assignment is inventory-audited, not implementation-ready; "
                "native readiness is not yet machine-mapped",
            )

    unfinished_current = (
        current.task_id != command.task_id
        and STATUS_RANK[current.status.value] < STATUS_RANK["reviewed"]
    )
    print(f"Selection preview: {command.task_id} ({command.kind})")
    print("Machine prerequisites: " + ("passed" if not machine_failures else "blocked"))
    for failure in machine_failures:
        print(f"  - {failure}")
    if command.kind == "external":
        print(f"Integration status: {command.integration_status}")
        print(f"Companion runtime: {command.companion_runtime}")
        print(f"Official runtime: {command.official_runtime}")
        print(
            "Problem-group prerequisites: "
            + (", ".join(command.group_prerequisites) if command.group_prerequisites else "none")
        )
        print("Learner status scope: companion-runtime-only")
    if unfinished_current:
        print(
            f"Current task {current.task_id} is {current.status.value}; selecting another "
            "task would pause it without granting a pass."
        )
    print("Human/readiness/resource gates: review the Task Card; not machine-proven.")
    if not args.apply:
        print("Dry run only: no state files were changed.")
        return 0 if not machine_failures else 1
    if machine_failures:
        raise TaskSelectionError("machine prerequisites are not satisfied")
    if not args.acknowledge_human_gates:
        raise TaskSelectionError("--acknowledge-human-gates is required before applying")
    if unfinished_current and not args.acknowledge_paused_current:
        raise TaskSelectionError(
            "current task is below reviewed; use --acknowledge-paused-current to pause it without passing"
        )
    if current.task_id == command.task_id:
        print("Already current: no files changed.")
        return 0
    _write_selection(
        repo_root=repo_root,
        ledger_path=ledger_path,
        current_path=current_path,
        command=command,
        snapshots=snapshots,
        selection_reason="Select one validated task after explicit human Gate attestation.",
    )
    print(f"Selected {command.task_id}; implementation status remains not_started or prior state.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        repo_root = args.repo_root.resolve(strict=True)
        ledger_path = repo_root / "state" / "TASK_LEDGER.jsonl"
        current_path = repo_root / "state" / "CURRENT_TASK.md"
        state_dir = _safe_state_directory(
            repo_root,
            ledger_path=ledger_path,
            current_path=current_path,
        )
        catalog, _, _ = validate_repository(repo_root=repo_root)
        native_ids = {task["id"] for task in catalog["tasks"]}
        manifests: Sequence[Mapping[str, Any]] = ()
        if args.task_id not in native_ids:
            _, manifests, _ = validate_external_courses(repo_root=repo_root)
        command = resolve_task(
            args.task_id,
            native_catalog=catalog,
            external_manifests=manifests,
        )
        operation = lambda: _run_selection(
            args=args,
            repo_root=repo_root,
            ledger_path=ledger_path,
            current_path=current_path,
            catalog=catalog,
            manifests=manifests,
            command=command,
        )
        if args.apply:
            with _selection_lock(state_dir):
                return operation()
        return operation()
    except (
        CurriculumValidationError,
        StateValidationError,
        TaskSelectionError,
    ) as error:
        print(f"TASK SELECTION REFUSED: {error}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as error:
        print(
            f"TASK SELECTION REFUSED: state files could not be updated safely "
            f"({type(error).__name__})",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
