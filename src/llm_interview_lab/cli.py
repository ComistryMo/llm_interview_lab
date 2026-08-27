"""Clone-first command line for the LEAN-V2 training lifecycle."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
from typing import Sequence

import yaml

from .catalog import Catalog, CatalogError, Problem, load_catalog
from .events import EventError, append_event, read_events, reduce_events
from .grader import GraderError, run_public_tests
from .lifecycle import LifecycleError, ReviewInput, record_review
from .submissions import SubmissionError, inspect_submission
from .workspace import (
    WorkspaceError, ensure_profile_is_ignored, event_schema_path, find_repository_root,
    init_profile, load_profile, profile_paths, retention_due_at, start_problem,
    start_retention, validate_profile_data,
)


class CliError(RuntimeError):
    """A concise user-facing command error."""


def _profile_state(repo_root: Path, profile_id: str):
    paths = profile_paths(repo_root, profile_id)
    profile = load_profile(paths, repo_root)
    events = read_events(paths.events_file, event_schema_path(repo_root))
    return paths, profile, events, reduce_events(events)


def _attempt(state, problem_id: str):
    attempt = state.latest_attempt(problem_id)
    if attempt is None:
        raise CliError(f"problem is not started: {problem_id}")
    return attempt


def _submission(repo_root: Path, attempt) -> Path:
    if attempt.submission_relpath is None:
        raise CliError("current attempt has no submission path")
    return repo_root.joinpath(*attempt.submission_relpath.split("/"))


def _require_ready(problem: Problem) -> None:
    if not problem.ready:
        raise CliError(f"problem is planned and has no runnable assets: {problem.id}")


def _require_prerequisites(problem: Problem, state) -> None:
    missing = sorted(set(problem.prerequisites) - state.mastered)
    if missing:
        raise CliError(f"prerequisites are not mastered: {', '.join(missing)}")


def _doctor(repo_root: Path) -> int:
    checks: list[tuple[str, bool, str]] = [("python", sys.version_info >= (3, 10), f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")]
    try:
        catalog = load_catalog(repo_root)
    except CatalogError as error:
        checks.append(("catalog", False, str(error)))
    else:
        ready = sum(problem.ready for problem in catalog.problems.values())
        checks.append(("catalog", True, f"{ready} ready / {len(catalog.problems) - ready} planned, DAG valid"))
    try:
        demo_data = yaml.safe_load((repo_root / "workspace/demo/profile.yaml").read_text(encoding="utf-8"))
        demo = validate_profile_data(demo_data, repo_root)
        if demo["synthetic"] is not True:
            raise WorkspaceError("demo profile must be explicitly synthetic")
        demo_state = reduce_events(read_events(repo_root / "workspace/demo/events.jsonl", event_schema_path(repo_root)))
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
    tracked = subprocess.run(["git", "-C", str(repo_root), "ls-files", "--", "workspace/profiles"], check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    names = [line.strip() for line in tracked.stdout.splitlines() if line.strip()]
    tracked_ok = tracked.returncode == 0 and names in ([], ["workspace/profiles/.gitkeep"])
    checks.append(("tracked-profiles", tracked_ok, "only the placeholder is tracked" if tracked_ok else "real Profile file is tracked"))
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


def _init(repo_root: Path, profile_id: str, tracks: tuple[str, ...], catalog: Catalog) -> int:
    requested = tracks or ("ai_foundation",)
    unknown = set(requested) - set(catalog.tracks)
    if unknown:
        raise CliError(f"unknown track: {', '.join(sorted(unknown))}")
    result = init_profile(repo_root, profile_id, requested)
    print(f"PROFILE {profile_id}: {'created' if result.created else 'already exists'}")
    print(f"TRACKS: {', '.join(requested)}")
    print(f"NEXT: llm-lab next --profile {profile_id}")
    return 0


def _next(repo_root: Path, profile_id: str, catalog: Catalog) -> int:
    _, profile, _, state = _profile_state(repo_root, profile_id)
    current = state.current_attempt()
    if current and state.problem_status(current.problem_id) == "mastered":
        current = None
    print("PROFILE")
    print(f"  {profile_id}")
    print("CURRENT")
    if current:
        problem = catalog.get(current.problem_id)
        print(f"  {problem.id} {problem.title}  {state.problem_status(problem.id)}")
        print("PREREQUISITES")
        if problem.prerequisites:
            for required in problem.prerequisites:
                print(f"  {required}  {state.problem_status(required)}")
        else:
            print("  none")
    else:
        print("  none")
        print("PREREQUISITES")
        print("  none")
    review_due = [attempt for attempt in state.attempts.values() if attempt.implemented and not attempt.reviewed]
    print("DUE REVIEWS")
    if review_due:
        for attempt in review_due[:3]:
            print(f"  {attempt.problem_id} {attempt.attempt_id}")
    else:
        print("  none")
    now = datetime.now().astimezone()
    retention_due: list[tuple[str, str]] = []
    for problem_id in state.reviewed_at:
        if problem_id not in state.retained_d2 and now >= retention_due_at(state, problem_id, "d2"):
            retention_due.append((problem_id, "d2"))
        elif problem_id in state.retained_d2 and problem_id not in state.retained_d7 and now >= retention_due_at(state, problem_id, "d7"):
            retention_due.append((problem_id, "d7"))
    print("DUE RETENTION")
    if retention_due:
        for problem_id, stage in retention_due[:3]:
            print(f"  {problem_id} {stage}")
    else:
        print("  none")
    unlocked = catalog.unlocked(state.mastered, set(profile["target_roles"]))[:3]
    print("UNLOCKS")
    if unlocked:
        for problem in unlocked:
            print(f"  {problem.id} {problem.title}")
    else:
        print("  none")
    print("COMMAND")
    if current and not current.implemented:
        command = f"llm-lab test {current.problem_id} --profile {profile_id}"
    elif review_due:
        command = f"llm-lab review {review_due[0].problem_id} --profile {profile_id} --help"
    elif retention_due:
        command = f"llm-lab retain {retention_due[0][0]} --stage {retention_due[0][1]} --profile {profile_id}"
    elif unlocked:
        command = f"llm-lab start {unlocked[0].id} --profile {profile_id}"
    else:
        command = "no action is currently available"
    print(f"  {command}")
    return 0


def _show(problem: Problem) -> int:
    print(f"{problem.id}  {problem.title}")
    print(f"STATUS  {problem.status}")
    print(f"PREREQUISITES  {', '.join(problem.prerequisites) or 'none'}")
    if not problem.ready or problem.problem_dir is None:
        print(f"DESCRIPTION  {problem.raw['description']}")
        return 0
    try:
        print("\n" + (problem.problem_dir / "task.md").read_text(encoding="utf-8").rstrip())
    except (OSError, UnicodeError) as error:
        raise CliError("problem task cannot be read") from error
    return 0


def _start(repo_root: Path, profile_id: str, problem: Problem) -> int:
    _require_ready(problem)
    _, _, _, state = _profile_state(repo_root, profile_id)
    _require_prerequisites(problem, state)
    result = start_problem(repo_root, profile_id, problem)
    print(f"ATTEMPT {result.attempt_id}: {'created' if result.created else 'reused without overwrite'}")
    print(f"SUBMISSION {result.submission_path.relative_to(repo_root).as_posix()}")
    print(f"TEST llm-lab test {problem.id} --profile {profile_id}")
    return 0


def _test(repo_root: Path, profile_id: str, problem: Problem) -> int:
    _require_ready(problem)
    paths, _, _, state = _profile_state(repo_root, profile_id)
    attempt = _attempt(state, problem.id)
    assert problem.public_tests is not None and problem.symbol is not None
    result = run_public_tests(
        repo_root=repo_root, test_path=problem.public_tests,
        submission_path=_submission(repo_root, attempt), submissions_root=paths.submissions_root,
        expected_symbol=problem.symbol, time_limit_ms=problem.time_limit_ms, output_limit_kb=problem.output_limit_kb,
    )
    append_event(paths.events_file, event_schema_path(repo_root), profile_id=profile_id, event_type="public_tests_run", problem_id=problem.id, attempt_id=attempt.attempt_id, payload={
        "submission_sha256": result.submission_sha256, "exit_code": result.exit_code, "status": result.status,
        "passed": result.passed, "failed": result.failed, "duration_ms": result.duration_ms,
    })
    if result.output:
        print(result.output)
    print(f"\nPUBLIC TESTS: {result.status.upper()}")
    print("MASTERY: NOT YET")
    return 0 if result.status == "passed" else 1 if result.status == "failed" else 2


def _submit(repo_root: Path, profile_id: str, problem: Problem) -> int:
    paths, _, _, state = _profile_state(repo_root, profile_id)
    attempt = _attempt(state, problem.id)
    inspected = inspect_submission(_submission(repo_root, attempt), paths.submissions_root)
    if attempt.implemented:
        if attempt.implemented_sha256 != inspected.sha256:
            raise CliError("implemented submission changed; start a retention attempt when eligible")
        print("SUBMISSION: ALREADY IMPLEMENTED")
        print(f"STATUS: {state.problem_status(problem.id)}")
        return 0
    passed = bool(attempt.last_public_test and attempt.last_public_test["status"] == "passed" and attempt.last_public_test["submission_sha256"] == inspected.sha256)
    append_event(paths.events_file, event_schema_path(repo_root), profile_id=profile_id, event_type="submission_created", problem_id=problem.id, attempt_id=attempt.attempt_id, payload={"submission_sha256": inspected.sha256, "public_tests_current_and_passed": passed})
    if not passed:
        print("SUBMISSION: RECORDED, BUT CURRENT PUBLIC TEST EVIDENCE IS NOT PASSING")
        print(f"RUN: llm-lab test {problem.id} --profile {profile_id}")
        print("MASTERY: NOT YET")
        return 1
    result = append_event(paths.events_file, event_schema_path(repo_root), profile_id=profile_id, event_type="task_implemented", problem_id=problem.id, attempt_id=attempt.attempt_id, payload={"submission_sha256": inspected.sha256})
    print("SUBMISSION: IMPLEMENTED" if result.appended else "SUBMISSION: ALREADY IMPLEMENTED")
    print("CONTRACT REVIEW: PENDING\nORAL DEFENSE: PENDING\nMASTERY: NOT YET")
    return 0


def _review(repo_root: Path, args) -> int:
    result = record_review(repo_root, args.profile, args.problem_id, ReviewInput(args.contract, args.oral, args.explanation, args.complexity, args.boundaries))
    print(f"REVIEW: {'PASS' if args.contract == args.oral == 'passed' else 'FAIL'}")
    print(f"STATUS: {result.status}")
    print(f"MASTERY: {'MASTERED' if result.mastered else 'NOT YET'}")
    return 0 if args.contract == args.oral == "passed" else 1


def _retain(repo_root: Path, profile_id: str, problem: Problem, stage: str) -> int:
    _require_ready(problem)
    result = start_retention(repo_root, profile_id, problem, stage)
    print(f"RETENTION {stage.upper()} {result.attempt_id}: {'created' if result.created else 'reused'}")
    print("OLD SUBMISSION: NOT COPIED")
    print(f"SUBMISSION {result.submission_path.relative_to(repo_root).as_posix()}")
    print(f"TEST llm-lab test {problem.id} --profile {profile_id}")
    return 0


def _catalog(catalog: Catalog, track_id: str | None) -> int:
    if track_id and track_id not in catalog.tracks:
        raise CliError(f"unknown track: {track_id}")
    for problem_id in catalog.order:
        problem = catalog.problems[problem_id]
        if track_id and track_id not in problem.raw["tracks"]:
            continue
        print(f"{problem.id:<9} {problem.status:<7} {problem.raw['tier']:<8} {problem.title}")
    return 0


def _graph(catalog: Catalog, track_id: str) -> int:
    if track_id not in catalog.tracks:
        raise CliError(f"unknown track: {track_id}")
    print(f"TRACK {track_id} — {catalog.tracks[track_id].title}")
    for problem_id in catalog.order:
        problem = catalog.problems[problem_id]
        if track_id in problem.raw["tracks"]:
            print(f"{problem.id} <- {', '.join(problem.prerequisites) or 'root'} [{problem.status}]")
    return 0


def _profile_show(repo_root: Path, profile_id: str) -> int:
    _, profile, _, state = _profile_state(repo_root, profile_id)
    print(f"PROFILE {profile_id}")
    print(f"TRACKS {', '.join(profile['target_roles'])}")
    for status in ("in_progress", "implemented", "reviewed", "retained_d2", "retained_d7", "mastered"):
        count = sum(state.problem_status(problem_id) == status for problem_id, _ in state.attempts)
        print(f"{status.upper()} {count}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-lab", description="Repository-local AI algorithm interview training")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    init = commands.add_parser("init"); init.add_argument("--profile", required=True); init.add_argument("--track", action="append", default=[])
    nxt = commands.add_parser("next"); nxt.add_argument("--profile", required=True)
    show = commands.add_parser("show"); show.add_argument("problem_id")
    start = commands.add_parser("start"); start.add_argument("problem_id"); start.add_argument("--profile", required=True)
    test = commands.add_parser("test"); test.add_argument("problem_id"); test.add_argument("--profile", required=True)
    submit = commands.add_parser("submit"); submit.add_argument("problem_id"); submit.add_argument("--profile", required=True)
    review = commands.add_parser("review"); review.add_argument("problem_id"); review.add_argument("--profile", required=True); review.add_argument("--contract", choices=("passed", "failed"), required=True); review.add_argument("--oral", choices=("passed", "failed"), required=True); review.add_argument("--explanation", required=True); review.add_argument("--complexity", required=True); review.add_argument("--boundaries", required=True)
    retain = commands.add_parser("retain"); retain.add_argument("problem_id"); retain.add_argument("--stage", choices=("d2", "d7"), required=True); retain.add_argument("--profile", required=True)
    listing = commands.add_parser("catalog"); listing.add_argument("--track")
    graph = commands.add_parser("graph"); graph.add_argument("--track", required=True)
    profile = commands.add_parser("profile"); profile_sub = profile.add_subparsers(dest="profile_command", required=True); profile_show = profile_sub.add_parser("show"); profile_show.add_argument("profile_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        repo_root = find_repository_root()
        if args.command == "doctor":
            return _doctor(repo_root)
        catalog = load_catalog(repo_root)
        if args.command == "init": return _init(repo_root, args.profile, tuple(args.track), catalog)
        if args.command == "next": return _next(repo_root, args.profile, catalog)
        if args.command == "catalog": return _catalog(catalog, args.track)
        if args.command == "graph": return _graph(catalog, args.track)
        if args.command == "profile": return _profile_show(repo_root, args.profile_id)
        problem = catalog.get(args.problem_id)
        if args.command == "show": return _show(problem)
        if args.command == "start": return _start(repo_root, args.profile, problem)
        if args.command == "test": return _test(repo_root, args.profile, problem)
        if args.command == "submit": return _submit(repo_root, args.profile, problem)
        if args.command == "review": return _review(repo_root, args)
        if args.command == "retain": return _retain(repo_root, args.profile, problem, args.stage)
        raise CliError("unknown command")
    except (CatalogError, CliError, EventError, GraderError, LifecycleError, SubmissionError, WorkspaceError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
