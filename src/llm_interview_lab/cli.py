"""Clone-first command line for the LEAN-V2 training lifecycle."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Sequence

import yaml

from .catalog import Catalog, CatalogError, Problem, load_catalog
from .context import (
    ContextError,
    build_interview_context,
    build_practice_context,
    serialize_context,
)
from .events import (
    EventError,
    append_event,
    read_events,
    reduce_events,
    summarize_mistakes,
)
from .grader import GraderError, run_public_tests
from .lifecycle import LifecycleError, ReviewInput, record_review
from .interviews import (
    ASSESSOR_SOURCES,
    CONFIDENCE_LEVELS,
    DIFFICULTY_RANGES,
    DURATIONS,
    INTERVIEWER_SOURCES,
    MODES,
    SUBJECTIVE_DIMENSIONS,
    InterviewError,
    create_interview,
    current_question,
    finish_interview,
    interview_candidates,
    list_interviews,
    load_session,
    reference_warnings,
    record_answer,
    record_assessment,
    record_delivered_question,
    report_interview,
    run_coding_test,
    start_interview,
)
from .materials import MATERIAL_KINDS, MaterialError, add_material, get_material, list_materials
from .submissions import SubmissionError, inspect_submission
from .workspace import (
    WorkspaceError, ensure_profile_is_ignored, event_schema_path, find_repository_root,
    init_profile, load_profile, profile_paths, retention_due_at, start_problem,
    start_retention, update_career_intent, validate_profile_data,
)


class CliError(RuntimeError):
    """A concise user-facing command error."""


def _read_private_text(path_value: str, label: str, max_characters: int) -> str:
    path = Path(path_value)
    try:
        value = os.lstat(path)
        attributes = getattr(value, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if stat.S_ISLNK(value.st_mode) or bool(attributes & reparse_flag) or not path.is_file():
            raise CliError(f"{label} file must be a regular, unlinked file")
        content = path.read_text(encoding="utf-8")
    except CliError:
        raise
    except (OSError, UnicodeError) as error:
        raise CliError(f"{label} file must be readable UTF-8 text") from error
    if len(content) > max_characters:
        raise CliError(f"{label} file exceeds {max_characters} characters")
    return content


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


def _allow_experimental(profile: dict, explicit: bool) -> bool:
    return explicit or bool(profile["preferences"].get("allow_experimental_problems", False))


def _require_quality(problem: Problem, profile: dict, explicit: bool) -> None:
    if not problem.recommendable and not _allow_experimental(profile, explicit):
        raise CliError(
            f"problem is contract-only: {problem.id}; use --allow-experimental "
            "or set preferences.allow_experimental_problems=true"
        )


def _require_prerequisites(problem: Problem, state) -> None:
    missing = sorted(set(problem.prerequisites) - state.mastered)
    if missing:
        raise CliError(f"prerequisites are not mastered: {', '.join(missing)}")


def _difficulty_label(problem: Problem) -> str:
    value = problem.raw["difficulty"]
    return (
        f"concept={value['concept']} coding={value['coding']} "
        f"debugging={value['debugging']}"
    )


def _doctor(repo_root: Path) -> int:
    checks: list[tuple[str, bool, str]] = [("python", sys.version_info >= (3, 10), f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")]
    try:
        catalog = load_catalog(repo_root)
    except CatalogError as error:
        checks.append(("catalog", False, str(error)))
    else:
        ready = sum(problem.ready for problem in catalog.problems.values())
        oracle = sum(problem.ready and problem.raw["validation"]["level"] in {"oracle", "field", "stable"} for problem in catalog.problems.values())
        retention = sum(problem.ready and all(problem.retention_variant(repo_root, stage) for stage in ("d2", "d7")) for problem in catalog.problems.values())
        field_runs = sum(problem.field_runs for problem in catalog.problems.values() if problem.ready)
        checks.append(("catalog", True, f"{ready} ready / {len(catalog.problems) - ready} planned, {oracle} oracle, {retention} retention-ready, {field_runs} field runs, DAG valid"))
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
    stored = load_profile(result.paths, repo_root)
    print(f"PROFILE {profile_id}: {'created' if result.created else 'already exists'}")
    print(f"TRACKS: {', '.join(stored['target_roles'])}")
    print(f"NEXT: llm-lab next --profile {profile_id}")
    return 0


def _next(
    repo_root: Path,
    profile_id: str,
    catalog: Catalog,
    include_experimental: bool = False,
    quest_id: str | None = None,
) -> int:
    _, profile, _, state = _profile_state(repo_root, profile_id)
    quest = None
    if quest_id is not None:
        try:
            quest = catalog.quests[quest_id]
        except KeyError as error:
            raise CliError(f"unknown quest: {quest_id}") from error
    current = state.current_attempt()
    if current and state.problem_status(current.problem_id) == "mastered":
        current = None
    print("PROFILE")
    print(f"  {profile_id}")
    if quest is not None:
        print("QUEST")
        print(f"  {quest.id} {quest.title}")
    print("CURRENT")
    if current:
        problem = catalog.get(current.problem_id)
        print(
            f"  {problem.id} {problem.title}  {state.problem_status(problem.id)}  "
            f"validation={problem.validation_level} "
            f"difficulty={_difficulty_label(problem)}"
        )
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
    mastery_blocked: list[str] = []
    for problem_id in state.reviewed_at:
        problem = catalog.get(problem_id)
        stage = "d2" if problem_id not in state.retained_d2 else "d7"
        if problem_id in state.retained_d7:
            continue
        if problem.retention_variant(repo_root, stage) is None:
            mastery_blocked.append(problem_id)
        elif now >= retention_due_at(state, problem_id, stage):
            retention_due.append((problem_id, stage))
    print("DUE RETENTION")
    if retention_due:
        for problem_id, stage in retention_due[:3]:
            print(f"  {problem_id} {stage}")
    else:
        print("  none")
    print("MASTERY BLOCKED")
    if mastery_blocked:
        for problem_id in mastery_blocked[:3]:
            print(f"  {problem_id} verified retention assets unavailable")
    else:
        print("  none")
    available = tuple(
        problem
        for problem in catalog.unlocked(
            state.mastered,
            set(profile["target_roles"]),
            include_experimental=_allow_experimental(profile, include_experimental),
        )
        if state.problem_status(problem.id) == "not_started"
    )
    if quest is None:
        unlocked = available[:3]
    else:
        by_id = {problem.id: problem for problem in available}
        unlocked = tuple(
            by_id[problem_id]
            for problem_id in quest.problem_ids
            if problem_id in by_id
        )[:3]
    print("UNLOCKS")
    if unlocked:
        for problem in unlocked:
            retention = "yes" if all(problem.retention_variant(repo_root, stage) for stage in ("d2", "d7")) else "no"
            print(
                f"  {problem.id} {problem.title}  assets={problem.status} "
                f"validation={problem.validation_level} retention={retention} "
                f"difficulty={_difficulty_label(problem)} field_runs={problem.field_runs}"
            )
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
    print(f"DIFFICULTY  {_difficulty_label(problem)}")
    if problem.ready:
        retention = "yes" if all(problem.raw["retention"].get(stage) and isinstance(problem.raw["retention"][stage], dict) and problem.raw["retention"][stage].get("oracle_validated") is True for stage in ("d2", "d7")) else "no"
        print(f"ASSETS  ready")
        print(f"VALIDATION  {problem.validation_level}")
        print(f"RETENTION  {retention}")
        print(f"FIELD RUNS  {problem.field_runs}")
    else:
        print("ASSETS  planned")
        print("VALIDATION  n/a")
        print("RETENTION  no")
        print("FIELD RUNS  0")
    print(f"PREREQUISITES  {', '.join(problem.prerequisites) or 'none'}")
    if not problem.ready or problem.problem_dir is None:
        print(f"DESCRIPTION  {problem.raw['description']}")
        return 0
    try:
        print("\n" + (problem.problem_dir / "task.md").read_text(encoding="utf-8").rstrip())
    except (OSError, UnicodeError) as error:
        raise CliError("problem task cannot be read") from error
    return 0


def _start(repo_root: Path, profile_id: str, problem: Problem, allow_experimental: bool = False) -> int:
    _require_ready(problem)
    _, profile, _, state = _profile_state(repo_root, profile_id)
    _require_quality(problem, profile, allow_experimental)
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
    test_path, expected_symbol = problem.public_tests, problem.symbol
    if attempt.retention_stage:
        variant = problem.retention_variant(repo_root, attempt.retention_stage)
        if variant is None or not attempt.retention_verified:
            raise CliError("mastery blocked: retention attempt is not backed by verified assets")
        _, test_path, expected_symbol = variant
    result = run_public_tests(
        repo_root=repo_root, test_path=test_path,
        submission_path=_submission(repo_root, attempt), submissions_root=paths.submissions_root,
        expected_symbol=expected_symbol, time_limit_ms=problem.time_limit_ms, output_limit_kb=problem.output_limit_kb,
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


def _catalog(repo_root: Path, catalog: Catalog, track_id: str | None) -> int:
    if track_id and track_id not in catalog.tracks:
        raise CliError(f"unknown track: {track_id}")
    for problem_id in catalog.order:
        problem = catalog.problems[problem_id]
        if track_id and track_id not in problem.raw["tracks"]:
            continue
        if problem.ready:
            retention = "yes" if all(problem.retention_variant(repo_root, stage) for stage in ("d2", "d7")) else "no"
            quality = f"validation={problem.validation_level} retention={retention} field_runs={problem.field_runs}"
        else:
            quality = "validation=n/a retention=no field_runs=0"
        difficulty = problem.raw["difficulty"]
        print(
            f"{problem.id:<12} assets={problem.status:<7} {quality} "
            f"difficulty=c{difficulty['concept']}/k{difficulty['coding']}/d{difficulty['debugging']}  "
            f"{problem.title}"
        )
    return 0


def _graph(
    catalog: Catalog,
    track_id: str | None = None,
    quest_id: str | None = None,
) -> int:
    if (track_id is None) == (quest_id is None):
        raise CliError("graph requires exactly one of --track or --quest")
    if quest_id is not None:
        try:
            quest = catalog.quests[quest_id]
        except KeyError as error:
            raise CliError(f"unknown quest: {quest_id}") from error
        print(f"QUEST {quest.id} - {quest.title}")
        print("ORDER is recommended; PREREQUISITES are the hard DAG")
        for index, problem_id in enumerate(quest.problem_ids, 1):
            problem = catalog.get(problem_id)
            print(
                f"{index:>2}. {problem.id} <- "
                f"{', '.join(problem.prerequisites) or 'root'} "
                f"[{problem.status}; {_difficulty_label(problem)}]"
            )
        return 0
    assert track_id is not None
    if track_id not in catalog.tracks:
        raise CliError(f"unknown track: {track_id}")
    print(f"TRACK {track_id} - {catalog.tracks[track_id].title}")
    for problem_id in catalog.order:
        problem = catalog.problems[problem_id]
        if track_id in problem.raw["tracks"]:
            print(
                f"{problem.id} <- {', '.join(problem.prerequisites) or 'root'} "
                f"[{problem.status}; {_difficulty_label(problem)}]"
            )
    return 0


def _profile_show(repo_root: Path, profile_id: str, as_json: bool = False) -> int:
    _, profile, _, state = _profile_state(repo_root, profile_id)
    problem_ids = {problem_id for problem_id, _ in state.attempts}
    counts = {
        status: sum(
            state.problem_status(problem_id) == status
            for problem_id in problem_ids
        )
        for status in (
            "in_progress",
            "implemented",
            "reviewed",
            "retained_d2",
            "retained_d7",
            "mastered",
        )
    }
    if as_json:
        print(
            json.dumps(
                {"profile": profile, "practice_status_counts": counts},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"PROFILE {profile_id}")
    print(f"TRACKS {', '.join(profile['target_roles'])}")
    intent = profile.get("career_intent")
    if intent:
        print(f"TARGET JOBS {', '.join(intent['target_job_titles']) or 'none'}")
        print(f"EMPLOYMENT STAGE {intent['employment_stage']}")
    for status, count in counts.items():
        print(f"{status.upper()} {count}")
    return 0


def _profile_configure(repo_root: Path, profile_id: str, career_file: str) -> int:
    content = _read_private_text(career_file, "career intent", 16_384)
    try:
        value = yaml.safe_load(content)
    except yaml.YAMLError as error:
        raise CliError("career intent file must contain valid YAML or JSON") from error
    if not isinstance(value, dict):
        raise CliError("career intent file must contain one object")
    updated = update_career_intent(repo_root, profile_id, value)
    intent = updated["career_intent"]
    print(f"PROFILE {profile_id}: career intent updated")
    print(f"TARGET JOBS {', '.join(intent['target_job_titles']) or 'none'}")
    print(f"EMPLOYMENT STAGE {intent['employment_stage']}")
    print("PRACTICE EVENTS: UNCHANGED")
    return 0


def _mistakes(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    *,
    unresolved_only: bool,
    as_json: bool,
) -> int:
    _, _, events, state = _profile_state(repo_root, profile_id)
    values = sorted(
        summarize_mistakes(events),
        key=lambda item: item.last_failed_sequence,
        reverse=True,
    )
    if unresolved_only:
        values = [item for item in values if not item.current_evidence_recovered]
    view = [
        {
            "problem_id": item.problem_id,
            "title": catalog.get(item.problem_id).title,
            "failure_count": item.failure_count,
            "last_failed_at": item.last_failed_at.isoformat(timespec="seconds"),
            "last_failure_kind": item.last_failure_kind,
            "recovered": item.current_evidence_recovered,
            "practice_status": state.problem_status(item.problem_id),
        }
        for item in values
    ]
    if as_json:
        print(json.dumps(view, ensure_ascii=False, indent=2))
        return 0
    print(f"MISTAKES {profile_id}")
    if not view:
        print("  none")
    for item in view:
        print(
            f"  {item['problem_id']} {item['title']} "
            f"failures={item['failure_count']} latest={item['last_failure_kind']} "
            f"recovered={'yes' if item['recovered'] else 'no'} "
            f"status={item['practice_status']}"
        )
    print("SOURCE events.jsonl (derived view; no separate mistake file)")
    return 0


def _material_add(repo_root: Path, args) -> int:
    record = add_material(
        repo_root,
        args.profile,
        Path(args.file),
        kind=args.kind,
        title=args.title,
        tags=tuple(args.tag),
        ai_access=args.allow_ai,
    )
    print(f"MATERIAL {record.id}: stored")
    print(f"KIND {record.kind}")
    print(f"AI ACCESS {'allowed' if record.ai_access else 'not allowed'}")
    print(f"SHA256 {record.sha256}")
    return 0


def _material_list(repo_root: Path, profile_id: str, as_json: bool) -> int:
    records = list_materials(repo_root, profile_id)
    if as_json:
        print(json.dumps([record.as_dict() for record in records], ensure_ascii=False, indent=2))
        return 0
    print(f"MATERIALS {profile_id}")
    if not records:
        print("  none")
    for record in records:
        print(
            f"  {record.id} kind={record.kind} "
            f"ai_access={'yes' if record.ai_access else 'no'} title={record.title}"
        )
    return 0


def _material_show(repo_root: Path, profile_id: str, material_id: str, as_json: bool) -> int:
    record = get_material(repo_root, profile_id, material_id)
    if as_json:
        print(json.dumps(record.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"MATERIAL {record.id}")
        print(f"TITLE {record.title}")
        print(f"KIND {record.kind}")
        print(f"AI ACCESS {'allowed' if record.ai_access else 'not allowed'}")
        print(f"TAGS {', '.join(record.tags) or 'none'}")
        print(f"SHA256 {record.sha256}")
        print("CONTENT not printed; material files are private local evidence")
    return 0


def _interview_summary(session: dict) -> dict:
    return {
        "interview_id": session["interview_id"],
        "status": session["status"],
        "configuration": session["configuration"],
        "material_ids": [item["id"] for item in session["material_refs"]],
        "material_refs": session["material_refs"],
        "selected_problem": session["selected_problem"],
        "rubric": session["rubric"],
        "question_plan": [
            {
                "question_id": item["question_id"],
                "kind": item["kind"],
                "timebox_minutes": item["timebox_minutes"],
                "material_ids": item["material_ids"],
                **(
                    {"problem_id": item["problem_id"]}
                    if "problem_id" in item
                    else {}
                ),
            }
            for item in session["questions"]
        ],
        "plan_fingerprint": session["plan_fingerprint"],
        "coding_submission_relpath": session["coding_submission_relpath"],
        "started_at": session["started_at"],
        "deadline": session["deadline"],
        "result": session["result"],
    }


def _context(repo_root: Path, catalog: Catalog, args) -> int:
    if args.mode == "interviewer":
        if args.interview is None:
            raise CliError("interviewer context requires --interview")
        if args.help_level is not None:
            raise CliError("interviewer context does not accept --help-level")
        value = build_interview_context(
            repo_root, catalog, args.profile, args.interview
        )
    else:
        if args.interview is not None:
            raise CliError("--interview is available only in interviewer mode")
        value = build_practice_context(
            repo_root,
            catalog,
            args.profile,
            args.mode,
            help_level=args.help_level,
        )
    print(serialize_context(value), end="")
    return 0


def _interview_candidates(repo_root: Path, catalog: Catalog, args) -> int:
    if args.limit < 1 or args.limit > 50:
        raise CliError("candidate limit must be from 1 to 50")
    _, _, _, state = _profile_state(repo_root, args.profile)
    problems = interview_candidates(
        catalog, track_id=args.track, difficulty=args.difficulty
    )[: args.limit]
    values = [
        {
            "problem_id": problem.id,
            "title": problem.title,
            "difficulty": problem.raw["difficulty"],
            "validation_level": problem.validation_level,
            "skills": problem.raw["skills"],
            "practice_status": state.problem_status(problem.id),
            "prerequisites": [
                {"problem_id": required, "status": state.problem_status(required)}
                for required in problem.prerequisites
            ],
        }
        for problem in problems
    ]
    if args.json:
        print(json.dumps(values, ensure_ascii=False, indent=2))
        return 0
    print(
        f"INTERVIEW CANDIDATES track={args.track} "
        f"difficulty={args.difficulty} profile={args.profile}"
    )
    if not values:
        print("  none")
    for item in values:
        print(
            f"  {item['problem_id']} {item['title']} "
            f"coding={item['difficulty']['coding']} "
            f"validation={item['validation_level']} "
            f"practice={item['practice_status']}"
        )
    print("AI MAY RECOMMEND; USER CONFIRMS WITH interview create --problem")
    return 0


def _interview_create(repo_root: Path, catalog: Catalog, args) -> int:
    session = create_interview(
        repo_root,
        args.profile,
        catalog,
        difficulty=args.difficulty,
        duration_minutes=args.duration,
        track_id=args.track,
        mode=args.mode,
        material_ids=tuple(args.material),
        consent_materials=args.consent_materials,
        problem_id=args.problem,
        focus=args.focus,
        seed=args.seed,
    )
    print(f"INTERVIEW {session['interview_id']}: ready")
    print(
        f"CONFIG difficulty={session['configuration']['difficulty']} "
        f"duration={session['configuration']['duration_minutes']}m "
        f"track={session['configuration']['track_id']} mode={session['configuration']['mode']}"
    )
    print(f"CODING {session['selected_problem']['problem_id']} {session['selected_problem']['title']}")
    print(
        f"PLAN sha256={session['plan_fingerprint']} "
        f"rubric={session['rubric']['version']}"
    )
    print("QUESTION PLAN")
    for question in session["questions"]:
        print(
            f"  {question['question_id']} kind={question['kind']} "
            f"timebox={question['timebox_minutes']}m"
        )
    if session["material_refs"]:
        print("MATERIAL CONSENT")
        for reference in session["material_refs"]:
            print(
                f"  {reference['id']} sha256={reference['sha256']} "
                f"use={reference['allowed_use']}"
            )
    else:
        print("MATERIAL CONSENT none")
    print(f"START llm-lab interview start {session['interview_id']} --profile {args.profile}")
    return 0


def _interview_list(repo_root: Path, catalog: Catalog, profile_id: str, as_json: bool) -> int:
    values = list_interviews(repo_root, profile_id, catalog)
    if as_json:
        print(json.dumps(values, ensure_ascii=False, indent=2))
        return 0
    print(f"INTERVIEWS {profile_id}")
    if not values:
        print("  none")
    for value in values:
        if value["status"] == "unreadable":
            print(f"  {value['interview_id']} status=unreadable")
            for warning in value.get("warnings", []):
                print(f"    warning={warning}")
            continue
        score = "n/a" if value["overall_score"] is None else f"{value['overall_score']:.1f}"
        print(
            f"  {value['interview_id']} status={value['status']} difficulty={value['difficulty']} "
            f"duration={value['duration_minutes']}m problem={value['problem_id']} score={score}"
        )
        for warning in value.get("warnings", []):
            print(f"    warning={warning}")
    return 0


def _interview_show(repo_root: Path, catalog: Catalog, profile_id: str, interview_id: str, as_json: bool) -> int:
    session = load_session(
        repo_root, profile_id, interview_id, catalog, verify_references=False
    )
    warnings = reference_warnings(repo_root, profile_id, session, catalog)
    value = _interview_summary(session)
    value["reference_warnings"] = list(warnings)
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    print(f"INTERVIEW {interview_id}")
    print(f"STATUS {session['status']}")
    print(
        f"CONFIG difficulty={session['configuration']['difficulty']} "
        f"duration={session['configuration']['duration_minutes']}m "
        f"track={session['configuration']['track_id']} mode={session['configuration']['mode']}"
    )
    print(f"CODING {session['selected_problem']['problem_id']} {session['selected_problem']['title']}")
    print(
        f"PLAN sha256={session['plan_fingerprint']} "
        f"rubric={session['rubric']['version']}"
    )
    print("QUESTION PLAN")
    for question in session["questions"]:
        print(
            f"  {question['question_id']} kind={question['kind']} "
            f"timebox={question['timebox_minutes']}m"
        )
    if session["material_refs"]:
        print("MATERIALS")
        for reference in session["material_refs"]:
            print(
                f"  {reference['id']} sha256={reference['sha256']} "
                f"use={reference['allowed_use']}"
            )
    else:
        print("MATERIALS none")
    print(f"FOCUS {session['configuration']['focus'] or 'none'}")
    print(f"DEADLINE {session['deadline'] or 'not started'}")
    if session["result"]:
        score_label = "SCORE" if session["result"]["completion_status"] == "completed" else "PARTIAL EVIDENCE SCORE"
        print(f"{score_label} {session['result']['overall_score']:.1f}")
        print(f"OUTCOME {session['result']['outcome']}")
    for warning in warnings:
        print(f"WARNING {warning}")
    return 0


def _interview_start(repo_root: Path, catalog: Catalog, profile_id: str, interview_id: str) -> int:
    session = start_interview(repo_root, profile_id, interview_id, catalog)
    print(f"INTERVIEW {interview_id}: {session['status']}")
    print(f"DEADLINE {session['deadline']}")
    print(
        "SUBMISSION "
        f"workspace/profiles/{profile_id}/{session['coding_submission_relpath']}"
    )
    print(f"CURRENT llm-lab interview current {interview_id} --profile {profile_id}")
    return 0


def _interview_current(repo_root: Path, catalog: Catalog, profile_id: str, interview_id: str, as_json: bool) -> int:
    value = current_question(repo_root, profile_id, interview_id, catalog)
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    print(f"INTERVIEW {interview_id} {value['status']}")
    print(f"REMAINING {value['remaining_seconds']} seconds")
    question = value["question"]
    if question:
        print(f"QUESTION {question['question_id']} kind={question['kind']} timebox={question['timebox_minutes']}m")
        print(f"PROMPT SOURCE {question.get('prompt_source', 'fixed')}")
        print(question["prompt"])
        if question["kind"] == "coding":
            print(f"TASK llm-lab show {question['problem_id']}")
            print(
                "SUBMISSION "
                f"workspace/profiles/{profile_id}/interviews/{interview_id}/coding/submission.py"
            )
            print(f"TEST llm-lab interview test {interview_id} --profile {profile_id}")
        else:
            if question.get("prompt_source") == "fixed":
                print(
                    "CUSTOMIZE "
                    f"llm-lab interview ask {interview_id} --profile {profile_id} "
                    f"--question {question['question_id']} --source ai --file QUESTION_FILE"
                )
            print(
                "ANSWER "
                f"llm-lab interview answer {interview_id} --profile {profile_id} "
                f"--question {question['question_id']} --file ANSWER_FILE"
            )
    elif value["status"] == "awaiting_score":
        print(f"MISSING ASSESSMENTS {', '.join(value['missing_assessments']) or 'none'}")
        print(f"SCORE llm-lab interview score {interview_id} --profile {profile_id} --help")
    elif value["status"] == "ready_to_finish":
        print("MISSING ASSESSMENTS none")
        print(f"FINISH llm-lab interview finish {interview_id} --profile {profile_id}")
    elif value["status"] == "expired":
        print(f"FINISH llm-lab interview finish {interview_id} --profile {profile_id}")
    return 0


def _interview_answer(repo_root: Path, catalog: Catalog, args) -> int:
    asked_question = args.asked
    if args.asked_file:
        asked_question = _read_private_text(
            args.asked_file, "asked question", 2000
        )
    session = record_answer(
        repo_root,
        args.profile,
        args.interview_id,
        catalog,
        args.question,
        Path(args.file),
        asked_question=asked_question,
    )
    print(f"ANSWER {args.question}: recorded")
    print(f"CURRENT llm-lab interview current {session['interview_id']} --profile {args.profile}")
    return 0


def _interview_ask(repo_root: Path, catalog: Catalog, args) -> int:
    text = args.text
    if args.file:
        text = _read_private_text(args.file, "delivered question", 2000)
    assert text is not None
    session = record_delivered_question(
        repo_root,
        args.profile,
        args.interview_id,
        catalog,
        args.question,
        text,
        source=args.source,
    )
    delivery = session["delivered_questions"][args.question]
    print(f"QUESTION {args.question}: delivered and archived")
    print(f"SOURCE {delivery['source']}")
    print(f"DELIVERED AT {delivery['delivered_at']}")
    print(
        f"ANSWER llm-lab interview answer {args.interview_id} "
        f"--profile {args.profile} --question {args.question} --file ANSWER_FILE"
    )
    return 0


def _interview_test(repo_root: Path, catalog: Catalog, profile_id: str, interview_id: str) -> int:
    result = run_coding_test(repo_root, profile_id, interview_id, catalog)
    if result.output:
        print(result.output)
    print(f"\nINTERVIEW CODING TESTS: {result.status.upper()}")
    print("PRACTICE MASTERY: UNCHANGED")
    return 0 if result.status == "passed" else 1 if result.status == "failed" else 2


def _interview_score(repo_root: Path, catalog: Catalog, args) -> int:
    evidence = args.evidence
    if args.evidence_file:
        evidence = _read_private_text(args.evidence_file, "evidence", 4000)
    session = record_assessment(
        repo_root,
        args.profile,
        args.interview_id,
        catalog,
        args.dimension,
        args.score,
        args.source,
        evidence,
        args.confidence,
        question_ids=tuple(args.question),
    )
    print(f"ASSESSMENT {args.dimension}: {session['assessments'][args.dimension]['score']:.1f}")
    print("SOURCE " + session["assessments"][args.dimension]["source"])
    return 0


def _interview_finish(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    interview_id: str,
    summary: str,
    summary_file: str | None,
    confirm_incomplete: bool,
) -> int:
    if summary_file:
        summary = _read_private_text(summary_file, "summary", 4000)
    session = finish_interview(
        repo_root,
        profile_id,
        interview_id,
        catalog,
        summary=summary,
        confirm_incomplete=confirm_incomplete,
    )
    result = session["result"]
    assert result is not None
    print(f"INTERVIEW {interview_id}: {result['completion_status']}")
    score_label = "SCORE" if result["completion_status"] == "completed" else "PARTIAL EVIDENCE SCORE"
    print(f"{score_label} {result['overall_score']:.1f}")
    print(f"ELAPSED {result['elapsed_seconds']} seconds")
    print(f"OUTCOME {result['outcome']}")
    print("PRACTICE MASTERY: UNCHANGED")
    print(f"REPORT llm-lab interview report {interview_id} --profile {profile_id}")
    return 0 if result["completion_status"] == "completed" else 1


def _interview_report(repo_root: Path, catalog: Catalog, profile_id: str, interview_id: str, format_name: str) -> int:
    print(report_interview(repo_root, profile_id, interview_id, catalog, format_name=format_name))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-lab", description="Repository-local AI algorithm interview training")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    init = commands.add_parser("init"); init.add_argument("--profile", required=True); init.add_argument("--track", action="append", default=[])
    nxt = commands.add_parser("next"); nxt.add_argument("--profile", required=True); nxt.add_argument("--include-experimental", action="store_true"); nxt.add_argument("--quest")
    show = commands.add_parser("show"); show.add_argument("problem_id")
    start = commands.add_parser("start"); start.add_argument("problem_id"); start.add_argument("--profile", required=True); start.add_argument("--allow-experimental", action="store_true")
    test = commands.add_parser("test"); test.add_argument("problem_id"); test.add_argument("--profile", required=True)
    submit = commands.add_parser("submit"); submit.add_argument("problem_id"); submit.add_argument("--profile", required=True)
    review = commands.add_parser("review"); review.add_argument("problem_id"); review.add_argument("--profile", required=True); review.add_argument("--contract", choices=("passed", "failed"), required=True); review.add_argument("--oral", choices=("passed", "failed"), required=True); review.add_argument("--explanation", required=True); review.add_argument("--complexity", required=True); review.add_argument("--boundaries", required=True)
    retain = commands.add_parser("retain"); retain.add_argument("problem_id"); retain.add_argument("--stage", choices=("d2", "d7"), required=True); retain.add_argument("--profile", required=True)
    listing = commands.add_parser("catalog"); listing.add_argument("--track")
    graph = commands.add_parser("graph")
    graph_target = graph.add_mutually_exclusive_group(required=True)
    graph_target.add_argument("--track")
    graph_target.add_argument("--quest")
    profile = commands.add_parser("profile")
    profile_sub = profile.add_subparsers(dest="profile_command", required=True)
    profile_show = profile_sub.add_parser("show")
    profile_show.add_argument("profile_id")
    profile_show.add_argument("--json", action="store_true")
    profile_configure = profile_sub.add_parser(
        "configure", help="replace structured, private career intent from YAML or JSON"
    )
    profile_configure.add_argument("profile_id")
    profile_configure.add_argument("--career-file", required=True)
    mistakes = commands.add_parser(
        "mistakes", help="derive a Profile's mistake view from events.jsonl"
    )
    mistakes.add_argument("--profile", required=True)
    mistakes.add_argument("--unresolved-only", action="store_true")
    mistakes.add_argument("--json", action="store_true")
    context = commands.add_parser(
        "context", help="emit bounded JSON for a bring-your-own AI"
    )
    context.add_argument("--profile", required=True)
    context.add_argument(
        "--mode", choices=("coach", "teacher", "reviewer", "interviewer"), required=True
    )
    context.add_argument("--help-level", choices=("H1", "H2", "H3"))
    context.add_argument("--interview")
    material = commands.add_parser("material", help="manage private career materials")
    material_sub = material.add_subparsers(dest="material_command", required=True)
    material_add = material_sub.add_parser("add", help="copy one explicit file into the ignored Profile")
    material_add.add_argument("--profile", required=True)
    material_add.add_argument("--kind", choices=sorted(MATERIAL_KINDS), required=True)
    material_add.add_argument("--file", required=True)
    material_add.add_argument("--title")
    material_add.add_argument("--tag", action="append", default=[])
    material_add.add_argument(
        "--allow-ai",
        action="store_true",
        help="make this text file eligible for later per-interview consent; this is not permanent consent",
    )
    material_list = material_sub.add_parser("list")
    material_list.add_argument("--profile", required=True)
    material_list.add_argument("--json", action="store_true")
    material_show = material_sub.add_parser("show")
    material_show.add_argument("material_id")
    material_show.add_argument("--profile", required=True)
    material_show.add_argument("--json", action="store_true")

    interview = commands.add_parser("interview", help="run profile-local timed mock interviews")
    interview_sub = interview.add_subparsers(dest="interview_command", required=True)
    interview_candidate = interview_sub.add_parser(
        "candidates", help="list deterministic Catalog candidates for an interviewer"
    )
    interview_candidate.add_argument("--profile", required=True)
    interview_candidate.add_argument("--track", required=True)
    interview_candidate.add_argument("--difficulty", choices=sorted(DIFFICULTY_RANGES), required=True)
    interview_candidate.add_argument("--limit", type=int, default=12)
    interview_candidate.add_argument("--json", action="store_true")
    interview_create = interview_sub.add_parser("create", help="freeze a local interview plan without starting its clock")
    interview_create.add_argument("--profile", required=True)
    interview_create.add_argument("--difficulty", choices=sorted(DIFFICULTY_RANGES), required=True)
    interview_create.add_argument("--duration", type=int, choices=sorted(DURATIONS), required=True)
    interview_create.add_argument("--track", required=True)
    interview_create.add_argument(
        "--mode",
        choices=sorted(MODES),
        default="catalog",
        help="catalog uses no materials; tailored freezes explicitly consented material IDs",
    )
    interview_create.add_argument("--material", action="append", default=[], help="repeat an AI-eligible material ID")
    interview_create.add_argument(
        "--consent-materials",
        action="store_true",
        help="consent to the listed IDs and their current SHA-256 for this interview only",
    )
    interview_create.add_argument("--problem", help="freeze an eligible Catalog problem chosen by you or your AI")
    interview_create.add_argument("--focus", default="", help="note for the BYO AI interviewer; not an automatic selector")
    interview_create.add_argument("--seed", type=int, default=0)
    interview_list = interview_sub.add_parser("list")
    interview_list.add_argument("--profile", required=True)
    interview_list.add_argument("--json", action="store_true")
    interview_show = interview_sub.add_parser("show")
    interview_show.add_argument("interview_id")
    interview_show.add_argument("--profile", required=True)
    interview_show.add_argument("--json", action="store_true")
    interview_start = interview_sub.add_parser("start")
    interview_start.add_argument("interview_id")
    interview_start.add_argument("--profile", required=True)
    interview_current = interview_sub.add_parser("current")
    interview_current.add_argument("interview_id")
    interview_current.add_argument("--profile", required=True)
    interview_current.add_argument("--json", action="store_true")
    interview_ask = interview_sub.add_parser(
        "ask", help="freeze an exact non-coding question delivered by an interviewer"
    )
    interview_ask.add_argument("interview_id")
    interview_ask.add_argument("--profile", required=True)
    interview_ask.add_argument("--question", required=True)
    interview_ask.add_argument("--source", choices=sorted(INTERVIEWER_SOURCES), required=True)
    delivered_group = interview_ask.add_mutually_exclusive_group(required=True)
    delivered_group.add_argument("--text")
    delivered_group.add_argument("--file")
    interview_answer = interview_sub.add_parser("answer")
    interview_answer.add_argument("interview_id")
    interview_answer.add_argument("--profile", required=True)
    interview_answer.add_argument("--question", required=True)
    interview_answer.add_argument("--file", required=True)
    asked_group = interview_answer.add_mutually_exclusive_group()
    asked_group.add_argument(
        "--asked", help="the exact personalized question asked by the interviewer"
    )
    asked_group.add_argument(
        "--asked-file",
        help="read the personalized question from local UTF-8 text instead of shell history",
    )
    interview_test = interview_sub.add_parser("test")
    interview_test.add_argument("interview_id")
    interview_test.add_argument("--profile", required=True)
    interview_score = interview_sub.add_parser("score")
    interview_score.add_argument("interview_id")
    interview_score.add_argument("--profile", required=True)
    interview_score.add_argument("--dimension", choices=SUBJECTIVE_DIMENSIONS, required=True)
    interview_score.add_argument("--score", type=float, required=True)
    interview_score.add_argument("--source", choices=sorted(ASSESSOR_SOURCES), required=True)
    evidence_group = interview_score.add_mutually_exclusive_group(required=True)
    evidence_group.add_argument("--evidence", help="specific, non-sensitive answer evidence supporting this score")
    evidence_group.add_argument("--evidence-file", help="read sensitive evidence from a local UTF-8 file instead of shell history")
    interview_score.add_argument("--confidence", choices=sorted(CONFIDENCE_LEVELS), required=True)
    interview_score.add_argument(
        "--question",
        action="append",
        required=True,
        help="completed q-NNN evidence reference; repeat when needed",
    )
    interview_finish = interview_sub.add_parser("finish")
    interview_finish.add_argument("interview_id")
    interview_finish.add_argument("--profile", required=True)
    summary_group = interview_finish.add_mutually_exclusive_group()
    summary_group.add_argument("--summary", default="", help="short, non-sensitive report summary")
    summary_group.add_argument("--summary-file", help="read the summary from a local UTF-8 file instead of shell history")
    interview_finish.add_argument(
        "--confirm-incomplete",
        action="store_true",
        help="finalize before the deadline even when required evidence is missing",
    )
    interview_report = interview_sub.add_parser("report")
    interview_report.add_argument("interview_id")
    interview_report.add_argument("--profile", required=True)
    interview_report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        repo_root = find_repository_root()
        if args.command == "doctor":
            return _doctor(repo_root)
        if args.command == "material":
            if args.material_command == "add": return _material_add(repo_root, args)
            if args.material_command == "list": return _material_list(repo_root, args.profile, args.json)
            if args.material_command == "show": return _material_show(repo_root, args.profile, args.material_id, args.json)
            raise CliError("unknown material command")
        catalog = load_catalog(repo_root)
        if args.command == "init": return _init(repo_root, args.profile, tuple(args.track), catalog)
        if args.command == "next": return _next(repo_root, args.profile, catalog, args.include_experimental, args.quest)
        if args.command == "catalog": return _catalog(repo_root, catalog, args.track)
        if args.command == "graph": return _graph(catalog, args.track, args.quest)
        if args.command == "profile":
            if args.profile_command == "show": return _profile_show(repo_root, args.profile_id, args.json)
            if args.profile_command == "configure": return _profile_configure(repo_root, args.profile_id, args.career_file)
            raise CliError("unknown profile command")
        if args.command == "mistakes": return _mistakes(repo_root, catalog, args.profile, unresolved_only=args.unresolved_only, as_json=args.json)
        if args.command == "context": return _context(repo_root, catalog, args)
        if args.command == "interview":
            if args.interview_command == "candidates": return _interview_candidates(repo_root, catalog, args)
            if args.interview_command == "create": return _interview_create(repo_root, catalog, args)
            if args.interview_command == "list": return _interview_list(repo_root, catalog, args.profile, args.json)
            if args.interview_command == "show": return _interview_show(repo_root, catalog, args.profile, args.interview_id, args.json)
            if args.interview_command == "start": return _interview_start(repo_root, catalog, args.profile, args.interview_id)
            if args.interview_command == "current": return _interview_current(repo_root, catalog, args.profile, args.interview_id, args.json)
            if args.interview_command == "ask": return _interview_ask(repo_root, catalog, args)
            if args.interview_command == "answer": return _interview_answer(repo_root, catalog, args)
            if args.interview_command == "test": return _interview_test(repo_root, catalog, args.profile, args.interview_id)
            if args.interview_command == "score": return _interview_score(repo_root, catalog, args)
            if args.interview_command == "finish": return _interview_finish(repo_root, catalog, args.profile, args.interview_id, args.summary, args.summary_file, args.confirm_incomplete)
            if args.interview_command == "report": return _interview_report(repo_root, catalog, args.profile, args.interview_id, args.format)
            raise CliError("unknown interview command")
        problem = catalog.get(args.problem_id)
        if args.command == "show": return _show(problem)
        if args.command == "start": return _start(repo_root, args.profile, problem, args.allow_experimental)
        if args.command == "test": return _test(repo_root, args.profile, problem)
        if args.command == "submit": return _submit(repo_root, args.profile, problem)
        if args.command == "review": return _review(repo_root, args)
        if args.command == "retain": return _retain(repo_root, args.profile, problem, args.stage)
        raise CliError("unknown command")
    except (CatalogError, CliError, ContextError, EventError, GraderError, InterviewError, LifecycleError, MaterialError, SubmissionError, WorkspaceError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
