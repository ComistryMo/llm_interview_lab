"""Minimal clone-first command line for the first LEAN-V2 vertical slice."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Sequence

import yaml

from .catalog import Catalog, CatalogError, Problem, load_catalog
from .events import EventError, append_event, read_events, reduce_events
from .grader import GraderError, run_public_tests
from .submissions import SubmissionError, inspect_submission
from .workspace import (
    WorkspaceError,
    ensure_profile_is_ignored,
    event_schema_path,
    find_repository_root,
    init_profile,
    load_profile,
    profile_paths,
    start_problem,
    validate_profile_data,
)


class CliError(RuntimeError):
    """A concise user-facing command error."""


def _load_profile_state(repo_root: Path, profile_id: str):
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    events = read_events(paths.events_file, event_schema_path(repo_root))
    return paths, events, reduce_events(events)


def _attempt_for_problem(state, problem_id: str):
    matching = [
        attempt
        for (candidate, _), attempt in state.attempts.items()
        if candidate == problem_id
    ]
    if not matching:
        raise CliError(f"problem is not started: {problem_id}")
    return matching[-1]


def _submission_path(repo_root: Path, attempt) -> Path:
    if attempt.submission_relpath is None:
        raise CliError("current attempt has no submission path")
    return repo_root.joinpath(*attempt.submission_relpath.split("/"))


def _implemented_problem_ids(state) -> set[str]:
    return {
        problem_id
        for problem_id, _ in state.attempts
        if state.problem_implemented(problem_id)
    }


def _assert_prerequisites(problem: Problem, state) -> None:
    missing = sorted(
        required
        for required in problem.prerequisites
        if not state.problem_implemented(required)
    )
    if missing:
        raise CliError(f"prerequisites are not implemented: {', '.join(missing)}")


def _doctor(repo_root: Path) -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(
        (
            "python",
            sys.version_info >= (3, 10),
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        )
    )
    try:
        catalog = load_catalog(repo_root)
    except CatalogError as error:
        checks.append(("catalog", False, str(error)))
    else:
        checks.append(("catalog", True, f"{len(catalog.problems)} problem(s), DAG valid"))

    try:
        demo_profile_path = repo_root / "workspace" / "demo" / "profile.yaml"
        demo_data = yaml.safe_load(demo_profile_path.read_text(encoding="utf-8"))
        demo = validate_profile_data(demo_data, repo_root)
        if demo["synthetic"] is not True:
            raise WorkspaceError("demo profile must be explicitly synthetic")
        demo_events = read_events(
            repo_root / "workspace" / "demo" / "events.jsonl",
            event_schema_path(repo_root),
        )
        demo_state = reduce_events(demo_events)
        if demo_state.profile_id != demo["profile_id"]:
            raise WorkspaceError("demo profile and events use different IDs")
    except (OSError, UnicodeError, yaml.YAMLError, WorkspaceError, EventError) as error:
        checks.append(("workspace-demo", False, str(error)))
    else:
        checks.append(("workspace-demo", True, "fictional demo schema valid"))

    try:
        ensure_profile_is_ignored(repo_root, "doctor-probe")
    except WorkspaceError as error:
        checks.append(("profile-ignore", False, str(error)))
    else:
        checks.append(("profile-ignore", True, "local profiles are ignored"))

    tracked = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", "workspace/profiles"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tracked_names = [line.strip() for line in tracked.stdout.splitlines() if line.strip()]
    tracked_ok = tracked.returncode == 0 and tracked_names in (
        [],
        ["workspace/profiles/.gitkeep"],
    )
    checks.append(
        (
            "tracked-profiles",
            tracked_ok,
            "only the placeholder is tracked" if tracked_ok else "real Profile file is tracked",
        )
    )

    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


def _init(repo_root: Path, profile_id: str) -> int:
    result = init_profile(repo_root, profile_id)
    verb = "created" if result.created else "already exists"
    print(f"PROFILE {profile_id}: {verb}")
    print(f"NEXT: llm-lab next --profile {profile_id}")
    return 0


def _next(repo_root: Path, profile_id: str, catalog: Catalog) -> int:
    _, _, state = _load_profile_state(repo_root, profile_id)
    current = state.current_attempt()
    print("PROFILE")
    print(f"  {profile_id}")
    print()
    print("CURRENT")
    if current is None:
        print("  none")
    else:
        problem = catalog.get(current.problem_id)
        if current.implemented:
            status = "implemented (mastery not yet)"
        elif current.revision_required:
            status = "in_progress (revision required)"
        elif current.last_public_test is not None:
            status = f"in_progress (public tests {current.last_public_test['status']})"
        else:
            status = "in_progress"
        print(f"  {problem.id} {problem.title}  {status}")
    print()
    print("DUE REVIEWS")
    print("  none in Vertical Slice 1")
    print()
    print("UNLOCKED")
    unlocked = catalog.unlocked(_implemented_problem_ids(state))[:3]
    if unlocked:
        for problem in unlocked:
            print(f"  {problem.id} {problem.title}")
    else:
        print("  none")
    print()
    print("COMMAND")
    if current is None and unlocked:
        print(f"  llm-lab start {unlocked[0].id} --profile {profile_id}")
    elif current is not None and not current.implemented:
        print(f"  llm-lab test {current.problem_id} --profile {profile_id}")
    else:
        print("  no further problem is available in Vertical Slice 1")
    return 0


def _show(problem: Problem) -> int:
    print(f"{problem.id}  {problem.title}")
    print(f"STATUS  {problem.status}")
    prerequisites = ", ".join(problem.prerequisites) or "none"
    print(f"PREREQUISITES  {prerequisites}")
    print()
    try:
        print((problem.problem_dir / "task.md").read_text(encoding="utf-8").rstrip())
    except (OSError, UnicodeError) as error:
        raise CliError("problem task cannot be read") from error
    return 0


def _start(repo_root: Path, profile_id: str, problem: Problem) -> int:
    _, _, state = _load_profile_state(repo_root, profile_id)
    _assert_prerequisites(problem, state)
    result = start_problem(repo_root, profile_id, problem)
    relative = result.submission_path.relative_to(repo_root).as_posix()
    verb = "created" if result.created else "reused without overwrite"
    print(f"ATTEMPT {result.attempt_id}: {verb}")
    print(f"SUBMISSION {relative}")
    print(f"TEST llm-lab test {problem.id} --profile {profile_id}")
    return 0


def _test(repo_root: Path, profile_id: str, problem: Problem) -> int:
    paths, _, state = _load_profile_state(repo_root, profile_id)
    attempt = _attempt_for_problem(state, problem.id)
    if problem.runner_kind != "pytest":
        raise CliError(f"unsupported runner: {problem.runner_kind}")
    result = run_public_tests(
        repo_root=repo_root,
        test_path=problem.public_tests,
        submission_path=_submission_path(repo_root, attempt),
        submissions_root=paths.submissions_root,
        expected_symbol=problem.symbol,
    )
    append_event(
        paths.events_file,
        event_schema_path(repo_root),
        profile_id=profile_id,
        event_type="public_tests_run",
        problem_id=problem.id,
        attempt_id=attempt.attempt_id,
        payload={
            "submission_sha256": result.submission_sha256,
            "exit_code": result.exit_code,
            "status": result.status,
            "passed": result.passed,
            "failed": result.failed,
            "duration_ms": result.duration_ms,
        },
    )
    if result.output:
        print(result.output)
    print()
    print(f"PUBLIC TESTS: {result.status.upper()}")
    print("MASTERY: NOT YET")
    return 0 if result.status == "passed" else 1 if result.status == "failed" else 2


def _submit(repo_root: Path, profile_id: str, problem: Problem) -> int:
    paths, _, state = _load_profile_state(repo_root, profile_id)
    attempt = _attempt_for_problem(state, problem.id)
    inspected = inspect_submission(
        _submission_path(repo_root, attempt),
        paths.submissions_root,
    )
    if attempt.implemented:
        implemented_sha = None
        events = read_events(paths.events_file, event_schema_path(repo_root))
        for event in events:
            if (
                event["event_type"] == "task_implemented"
                and event["problem_id"] == problem.id
                and event["attempt_id"] == attempt.attempt_id
            ):
                implemented_sha = event["payload"]["submission_sha256"]
        if implemented_sha != inspected.sha256:
            raise CliError("implemented submission changed; --new-attempt is not available")
        print("SUBMISSION: ALREADY IMPLEMENTED")
        print("MASTERY: NOT YET")
        return 0

    passed_current_sha = bool(
        attempt.last_public_test
        and attempt.last_public_test["status"] == "passed"
        and attempt.last_public_test["submission_sha256"] == inspected.sha256
    )
    append_event(
        paths.events_file,
        event_schema_path(repo_root),
        profile_id=profile_id,
        event_type="submission_created",
        problem_id=problem.id,
        attempt_id=attempt.attempt_id,
        payload={
            "submission_sha256": inspected.sha256,
            "public_tests_current_and_passed": passed_current_sha,
        },
    )
    if not passed_current_sha:
        print("SUBMISSION: RECORDED, BUT CURRENT PUBLIC TEST EVIDENCE IS NOT PASSING")
        print(f"RUN: llm-lab test {problem.id} --profile {profile_id}")
        print("MASTERY: NOT YET")
        return 1

    result = append_event(
        paths.events_file,
        event_schema_path(repo_root),
        profile_id=profile_id,
        event_type="task_implemented",
        problem_id=problem.id,
        attempt_id=attempt.attempt_id,
        payload={"submission_sha256": inspected.sha256},
    )
    print("SUBMISSION: IMPLEMENTED" if result.appended else "SUBMISSION: ALREADY IMPLEMENTED")
    print("CONTRACT REVIEW: PENDING")
    print("ORAL DEFENSE: PENDING")
    print("D+2 RETENTION: PENDING")
    print("D+7 RETENTION: PENDING")
    print("MASTERY: NOT YET")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-lab",
        description="Repository-local AI algorithm interview training",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="validate repository and public demo health")

    init_parser = commands.add_parser("init", help="create an ignored local Profile")
    init_parser.add_argument("--profile", required=True)

    next_parser = commands.add_parser("next", help="show one-screen training state")
    next_parser.add_argument("--profile", required=True)

    show_parser = commands.add_parser("show", help="show one fixed problem contract")
    show_parser.add_argument("problem_id")

    start_parser = commands.add_parser("start", help="create or reuse the current attempt")
    start_parser.add_argument("problem_id")
    start_parser.add_argument("--profile", required=True)

    test_parser = commands.add_parser("test", help="run exact public tests")
    test_parser.add_argument("problem_id")
    test_parser.add_argument("--profile", required=True)

    submit_parser = commands.add_parser("submit", help="record implementation evidence")
    submit_parser.add_argument("problem_id")
    submit_parser.add_argument("--profile", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        repo_root = find_repository_root()
        if args.command == "doctor":
            return _doctor(repo_root)
        if args.command == "init":
            return _init(repo_root, args.profile)
        catalog = load_catalog(repo_root)
        if args.command == "next":
            return _next(repo_root, args.profile, catalog)
        problem = catalog.get(args.problem_id)
        if args.command == "show":
            return _show(problem)
        if args.command == "start":
            return _start(repo_root, args.profile, problem)
        if args.command == "test":
            return _test(repo_root, args.profile, problem)
        if args.command == "submit":
            return _submit(repo_root, args.profile, problem)
        raise CliError("unknown command")
    except (
        CatalogError,
        CliError,
        EventError,
        GraderError,
        SubmissionError,
        WorkspaceError,
    ) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
