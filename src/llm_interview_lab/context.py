"""Small, deterministic context manifests for repository-aware AI clients.

The builders in this module are read-only generated views.  They deliberately
return paths and content identities instead of copying learner code, raw event
history, career-material bodies, or public tests into a model context.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from .catalog import Catalog, Problem
from .events import read_events, reduce_events, summarize_mistakes
from .interviews import current_question, load_session, reference_warnings
from .materials import get_material
from .role_interviews import (
    ROLE_INTERVIEW_ID_PREFIX,
    RoleInterviewError,
    current_role_question,
    load_role_interview,
)
from .submissions import SubmissionError, inspect_submission
from .workspace import (
    event_schema_path,
    load_profile,
    profile_paths,
    retention_due_at,
)


CONTEXT_SCHEMA_VERSION = 1
MAX_SERIALIZED_CONTEXT_BYTES = 8 * 1024
PRACTICE_MODES = frozenset({"coach", "teacher", "reviewer"})
HELP_LEVELS = frozenset({"H1", "H2", "H3"})
MAX_CONTEXT_CAREER_VALUES = 3
MAX_CONTEXT_MISTAKES = 3
EXCLUDED_CONTEXT = (
    "future_interview_prompts",
    "future_problem_assets",
    "material_bodies",
    "old_submissions",
    "other_profiles",
    "private_tests",
    "public_test_source",
    "raw_events",
)
MODE_PROMPTS = {
    "teacher": "coach/prompts/teacher.md",
    "reviewer": "coach/prompts/reviewer.md",
    "interviewer": "coach/prompts/interviewer.md",
}
HINT_HEADING_RE = re.compile(r"^##\s+(H[1-3])(?:\s|$)")


class ContextError(RuntimeError):
    """Raised when a minimal AI context cannot be produced safely."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ContextError(f"{label} cannot be read") from error


def _is_obvious_link(path: Path) -> bool:
    try:
        value = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(value, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(attributes & reparse_flag)


def _reject_linked_components(repo_root: Path, path: Path, label: str) -> None:
    lexical = path.absolute()
    root = repo_root.absolute()
    try:
        relative = lexical.relative_to(root)
    except ValueError as error:
        raise ContextError(f"{label} must remain inside the repository") from error
    current = root
    if _is_obvious_link(current):
        raise ContextError(f"{label} must not use a symlink or reparse point")
    for part in relative.parts:
        current /= part
        if _is_obvious_link(current):
            raise ContextError(f"{label} must not use a symlink or reparse point")


def _repo_relative(repo_root: Path, path: Path, label: str) -> str:
    _reject_linked_components(repo_root, path, label)
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            raise ContextError(f"{label} must be a regular file")
        return resolved.relative_to(repo_root.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as error:
        raise ContextError(f"{label} must remain inside the repository") from error


def _file_ref(repo_root: Path, path: Path, purpose: str) -> dict[str, str]:
    relative = _repo_relative(repo_root, path, purpose)
    content = _read_bytes(path, purpose)
    return {
        "path": relative,
        "purpose": purpose,
        "sha256": _sha256_bytes(content),
    }


def _policy_refs(repo_root: Path, mode: str) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "agents": _file_ref(repo_root, repo_root / "AGENTS.md", "repository_ai_policy"),
        "policy": _file_ref(repo_root, repo_root / "coach/POLICY.md", "coach_policy"),
        "mode_prompt": None,
    }
    prompt = MODE_PROMPTS.get(mode)
    if prompt is not None:
        refs["mode_prompt"] = _file_ref(
            repo_root, repo_root.joinpath(*prompt.split("/")), f"{mode}_mode_prompt"
        )
    return refs


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _with_fingerprint(value: dict[str, Any]) -> dict[str, Any]:
    snapshot = dict(value)
    snapshot.pop("state_fingerprint", None)
    value["state_fingerprint"] = _sha256_bytes(_canonical_bytes(snapshot))
    return value


def serialize_context(context: Mapping[str, Any]) -> str:
    """Serialize one context canonically and enforce its token-cost guardrail."""

    try:
        encoded = _canonical_bytes(context) + b"\n"
    except (TypeError, ValueError) as error:
        raise ContextError("AI context must contain JSON-serializable values") from error
    if len(encoded) > MAX_SERIALIZED_CONTEXT_BYTES:
        raise ContextError(
            f"AI context exceeds the {MAX_SERIALIZED_CONTEXT_BYTES}-byte limit"
        )
    return encoded.decode("utf-8")


def _retention_available(repo_root: Path, problem: Problem) -> bool:
    return all(problem.retention_variant(repo_root, stage) for stage in ("d2", "d7"))


def _problem_summary(repo_root: Path, problem: Problem, state: Any) -> dict[str, Any]:
    return {
        "id": problem.id,
        "title": problem.title,
        "status": state.problem_status(problem.id),
        "asset_status": problem.status,
        "validation_level": problem.validation_level,
        "retention_available": _retention_available(repo_root, problem),
        "prerequisites": [
            {"id": required, "status": state.problem_status(required)}
            for required in problem.prerequisites
        ],
    }


def _hint_section(repo_root: Path, path: Path, level: str) -> str:
    _repo_relative(repo_root, path, "current_hint_asset")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ContextError("current hint asset cannot be read as UTF-8") from error
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        match = HINT_HEADING_RE.match(line.strip())
        if match is None:
            continue
        if start is not None:
            end = index
            break
        if match.group(1) == level:
            start = index
    if start is None:
        raise ContextError(f"current problem does not define a {level} hint section")
    value = "\n".join(lines[start:end]).strip()
    if not value:
        raise ContextError(f"current problem has an empty {level} hint section")
    return value


def _attempt_submission(
    repo_root: Path,
    paths: Any,
    attempt: Any,
) -> tuple[dict[str, Any], dict[str, str]]:
    if attempt.submission_relpath is None:
        raise ContextError("current attempt has no submission path")
    submission = repo_root.joinpath(*attempt.submission_relpath.split("/"))
    try:
        inspected = inspect_submission(submission, paths.submissions_root)
    except SubmissionError as error:
        raise ContextError(f"current submission is unavailable: {error}") from error
    relative = _repo_relative(repo_root, inspected.path, "current_submission")
    return (
        {"path": relative, "sha256": inspected.sha256},
        {"path": relative, "purpose": "current_submission", "sha256": inspected.sha256},
    )


def _test_summary(attempt: Any, current_sha256: str) -> dict[str, Any] | None:
    evidence = attempt.last_public_test
    if evidence is None:
        return None
    allowed = (
        "submission_sha256",
        "exit_code",
        "status",
        "passed",
        "failed",
        "duration_ms",
        "output_truncated",
    )
    summary = {name: evidence[name] for name in allowed if name in evidence}
    summary["current_submission"] = evidence.get("submission_sha256") == current_sha256
    return summary


def _practice_due(
    repo_root: Path,
    catalog: Catalog,
    state: Any,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    reviews = sorted(
        (
            {"problem_id": attempt.problem_id, "attempt_id": attempt.attempt_id}
            for attempt in state.attempts.values()
            if attempt.implemented and not attempt.reviewed
        ),
        key=lambda item: (item["problem_id"], item["attempt_id"]),
    )[:3]
    now = datetime.now().astimezone()
    retention: list[dict[str, str]] = []
    for problem_id in sorted(state.reviewed_at):
        if problem_id in state.retained_d7:
            continue
        stage = "d2" if problem_id not in state.retained_d2 else "d7"
        problem = catalog.get(problem_id)
        if problem.retention_variant(repo_root, stage) is None:
            continue
        due_at = retention_due_at(state, problem_id, stage)
        if now >= due_at:
            retention.append(
                {
                    "problem_id": problem_id,
                    "stage": stage,
                    "due_at": due_at.isoformat(timespec="seconds"),
                }
            )
    return reviews, retention[:3]


def _coach_personalization(
    profile: Mapping[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return bounded current-profile facts without exposing raw event payloads."""

    stored_intent = profile.get("career_intent")
    career_intent: dict[str, Any] | None = None
    if isinstance(stored_intent, Mapping):
        list_fields = (
            "target_job_titles",
            "preferred_locations",
            "interview_languages",
            "priorities",
        )
        career_intent = {
            "target_job_titles": list(stored_intent["target_job_titles"])[
                :MAX_CONTEXT_CAREER_VALUES
            ],
            "employment_stage": stored_intent["employment_stage"],
            "preferred_locations": list(stored_intent["preferred_locations"])[
                :MAX_CONTEXT_CAREER_VALUES
            ],
            "interview_languages": list(stored_intent["interview_languages"])[
                :MAX_CONTEXT_CAREER_VALUES
            ],
            "priorities": list(stored_intent["priorities"])[
                :MAX_CONTEXT_CAREER_VALUES
            ],
            "truncated": any(
                len(stored_intent[field]) > MAX_CONTEXT_CAREER_VALUES
                for field in list_fields
            ),
        }

    mistakes = list(summarize_mistakes(events))
    # Stable sorts make unresolved evidence the primary signal and physical
    # event order the recency signal; timestamps remain display-only evidence.
    mistakes.sort(key=lambda item: item.problem_id)
    mistakes.sort(key=lambda item: item.last_failed_sequence, reverse=True)
    mistakes.sort(key=lambda item: item.current_evidence_recovered)
    recent_mistakes = [
        {
            "problem_id": item.problem_id,
            "failure_count": item.failure_count,
            "last_failure_kind": item.last_failure_kind,
            "last_failed_at": item.last_failed_at.isoformat(timespec="seconds"),
            "current_evidence_recovered": item.current_evidence_recovered,
        }
        for item in mistakes[:MAX_CONTEXT_MISTAKES]
    ]
    return {
        "career_intent": career_intent,
        "recent_mistakes": recent_mistakes,
    }


def build_practice_context(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    mode: str,
    help_level: str | None = None,
) -> dict[str, Any]:
    """Build a compact context for one current Practice task."""

    repo_root = repo_root.resolve()
    normalized_mode = mode.lower() if isinstance(mode, str) else ""
    if normalized_mode not in PRACTICE_MODES:
        raise ContextError("practice context mode must be coach, teacher, or reviewer")
    if help_level is not None and normalized_mode != "teacher":
        raise ContextError("help_level is available only in teacher mode")
    if normalized_mode == "teacher" and help_level is None:
        raise ContextError("teacher mode requires one explicit H1, H2, or H3 level")
    normalized_help = None if help_level is None else help_level.upper()
    if normalized_help is not None and normalized_help not in HELP_LEVELS:
        raise ContextError("teacher context supports only H1, H2, or H3")

    paths = profile_paths(repo_root, profile_id)
    profile = load_profile(paths, repo_root)
    events = read_events(paths.events_file, event_schema_path(repo_root))
    state = reduce_events(events)
    current_attempt = state.current_attempt()
    if (
        current_attempt is not None
        and state.problem_status(current_attempt.problem_id) == "mastered"
    ):
        current_attempt = None
    if normalized_mode in {"teacher", "reviewer"} and current_attempt is None:
        raise ContextError(f"{normalized_mode} mode requires a current Practice attempt")

    reviews, retention = _practice_due(repo_root, catalog, state)
    include_experimental = bool(
        profile["preferences"].get("allow_experimental_problems", False)
    )
    unlocked = [
        problem
        for problem in catalog.unlocked(
            state.mastered,
            set(profile["target_roles"]),
            include_experimental=include_experimental,
        )
        if state.problem_status(problem.id) == "not_started"
    ][:3]

    read_allowlist: list[dict[str, str]] = []
    current: dict[str, Any] | None = None
    if current_attempt is not None:
        problem = catalog.get(current_attempt.problem_id)
        if problem.problem_dir is None:
            raise ContextError("current Practice problem has no runnable assets")
        current = {
            "problem": _problem_summary(repo_root, problem, state),
            "attempt": {
                "attempt_id": current_attempt.attempt_id,
                "retention_stage": current_attempt.retention_stage,
            },
        }
        if normalized_mode in {"teacher", "reviewer"}:
            task_ref = _file_ref(
                repo_root, problem.problem_dir / "task.md", "current_task_contract"
            )
            current["task"] = {"path": task_ref["path"], "sha256": task_ref["sha256"]}
            read_allowlist.append(task_ref)
        if normalized_mode == "teacher":
            assert normalized_help is not None
            current["help"] = {
                "level": normalized_help,
                "content": _hint_section(
                    repo_root, problem.problem_dir / "hints.md", normalized_help
                ),
            }
        if normalized_mode == "reviewer":
            submission, submission_ref = _attempt_submission(
                repo_root, paths, current_attempt
            )
            current["submission"] = submission
            current["last_public_test"] = _test_summary(
                current_attempt, submission["sha256"]
            )
            read_allowlist.append(submission_ref)

    unlock_summaries = [
        {
            "id": problem.id,
            "title": problem.title,
            "validation_level": problem.validation_level,
            "prerequisites": list(problem.prerequisites),
        }
        for problem in unlocked
    ]
    if current_attempt is not None and not current_attempt.implemented:
        next_command = f"llm-lab test {current_attempt.problem_id} --profile {profile_id}"
    elif reviews:
        next_command = (
            f"llm-lab review {reviews[0]['problem_id']} --profile {profile_id} --help"
        )
    elif retention:
        next_command = (
            f"llm-lab retain {retention[0]['problem_id']} --stage "
            f"{retention[0]['stage']} --profile {profile_id}"
        )
    elif unlocked:
        next_command = f"llm-lab start {unlocked[0].id} --profile {profile_id}"
    else:
        next_command = "no action is currently available"

    value: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "mode": normalized_mode.upper(),
        "profile_id": profile_id,
        "scope": "practice",
        "policy_refs": _policy_refs(repo_root, normalized_mode),
        "state_fingerprint": "0" * 64,
        "current": current,
        "due": {"reviews": reviews, "retention": retention},
        "unlocks": unlock_summaries,
        "read_allowlist": read_allowlist,
        "commands": {"next": next_command},
        "excluded": list(EXCLUDED_CONTEXT),
    }
    if normalized_mode == "coach":
        value["personalization"] = _coach_personalization(profile, events)
    return _with_fingerprint(value)


def _profile_relative(repo_root: Path, profile_id: str, relative: str) -> Path:
    root = profile_paths(repo_root, profile_id).root
    return root.joinpath(*relative.split("/"))


def _interview_submission_ref(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    relative: str,
) -> tuple[dict[str, str], dict[str, str]]:
    path = _profile_relative(repo_root, profile_id, relative)
    coding_root = profile_paths(repo_root, profile_id).interviews_root / interview_id / "coding"
    try:
        inspected = inspect_submission(path, coding_root)
    except SubmissionError as error:
        raise ContextError(f"interview submission is unavailable: {error}") from error
    repo_path = _repo_relative(repo_root, inspected.path, "current_interview_submission")
    value = {"path": repo_path, "sha256": inspected.sha256}
    return value, {**value, "purpose": "current_interview_submission"}


def _completed_interview_evidence(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    profile_root = profile_paths(repo_root, profile_id).root
    question_by_id = {item["question_id"]: item for item in session["questions"]}
    evidence: list[dict[str, Any]] = []
    allowlist: list[dict[str, str]] = []
    for question_id in sorted(session["answers"]):
        answer = session["answers"][question_id]
        path = profile_root.joinpath(*answer["answer_relpath"].split("/"))
        ref = _file_ref(repo_root, path, f"answer_{question_id}")
        if ref["sha256"] != answer["sha256"]:
            raise ContextError(f"answer evidence changed after recording: {question_id}")
        question = question_by_id[question_id]
        evidence.append(
            {
                "question_id": question_id,
                "kind": question["kind"],
                "asked_question": answer["asked_question"],
                "answer": {"path": ref["path"], "sha256": ref["sha256"]},
            }
        )
        allowlist.append(ref)
    if session["coding_submission_relpath"] is not None:
        submission, ref = _interview_submission_ref(
            repo_root,
            profile_id,
            session["interview_id"],
            session["coding_submission_relpath"],
        )
        evidence.append(
            {
                "question_id": "q-004",
                "kind": "coding",
                "submission": submission,
                "grader": session["coding_evidence"],
            }
        )
        allowlist.append(ref)
    return evidence, allowlist


def _role_material_ref(
    repo_root: Path,
    profile_id: str,
    reference: Mapping[str, Any],
) -> dict[str, str]:
    if reference["allowed_use"] != "role_interview":
        raise ContextError("role interview material has no matching consent")
    record = get_material(repo_root, profile_id, reference["id"])
    if not record.ai_access or record.sha256 != reference["sha256"]:
        raise ContextError("role interview material consent is stale or revoked")
    material_path = profile_paths(repo_root, profile_id).root.joinpath(
        *record.relative_path.split("/")
    )
    return {
        "path": _repo_relative(
            repo_root, material_path, f"material_{reference['id']}"
        ),
        "purpose": "consented_role_interview_material",
        "sha256": record.sha256,
        "material_id": record.id,
        "allowed_use": reference["allowed_use"],
    }


def _build_role_interview_context(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    interview_id: str,
) -> dict[str, Any]:
    """Build a current-question-only view for one role-aware interview."""

    session = load_role_interview(repo_root, profile_id, interview_id)
    read_allowlist: list[dict[str, str]] = []
    commands: dict[str, str] = {}
    current: dict[str, Any]

    if session["status"] == "ready":
        current = {
            "status": "ready",
            "configuration": {
                "role_id": session["role_id"],
                "seniority": session["seniority"],
                "difficulty": session["difficulty"],
                "duration_minutes": session["duration_minutes"],
                "ai_mode": session["ai_mode"],
            },
            # Only timing and kinds are visible before the clock starts.
            "question_plan": [
                {
                    "question_id": question["question_id"],
                    "kind": question["kind"],
                    "timebox_minutes": question["timebox_minutes"],
                }
                for question in session["questions"]
            ],
        }
        commands["next"] = (
            f"llm-lab interview role-start {interview_id} --profile {profile_id}"
        )
    elif session["status"] == "active":
        try:
            stage = current_role_question(repo_root, profile_id, interview_id)
        except RoleInterviewError as error:
            if "expired" not in str(error):
                raise ContextError(str(error)) from error
            stage = {"question": None, "remaining_seconds": 0}
        question = stage["question"]
        current = {
            "status": "expired" if stage["remaining_seconds"] == 0 else "active",
            "deadline": session["deadline"],
            "remaining_seconds": stage["remaining_seconds"],
            "question": None,
        }
        if question is None:
            commands["next"] = (
                f"llm-lab interview role-finish {interview_id} --profile {profile_id}"
            )
        else:
            question_id = question["question_id"]
            current["question"] = {
                "question_id": question_id,
                "kind": question["kind"],
                "title": question["title"],
                "prompt": question["prompt"],
                "timebox_minutes": question["timebox_minutes"],
                "skills": question["skills"],
                "rubric": question["rubric"],
            }
            if question["kind"] == "coding":
                problem = catalog.get(question["source"]["id"])
                assert problem.problem_dir is not None
                task_ref = _file_ref(
                    repo_root,
                    problem.problem_dir / "task.md",
                    "interview_coding_contract",
                )
                submission_path = (
                    profile_paths(repo_root, profile_id).interviews_root
                    / interview_id
                    / "coding"
                    / question_id
                    / "submission.py"
                )
                try:
                    inspected = inspect_submission(
                        submission_path, submission_path.parent
                    )
                except SubmissionError as error:
                    raise ContextError(
                        f"current interview submission is unavailable: {error}"
                    ) from error
                submission_ref = _file_ref(
                    repo_root, inspected.path, "current_interview_submission"
                )
                current["coding"] = {
                    "contract": {
                        "path": task_ref["path"],
                        "sha256": task_ref["sha256"],
                    },
                    "submission": {
                        "path": submission_ref["path"],
                        "sha256": submission_ref["sha256"],
                    },
                    "grader": session["coding_evidence"].get(question_id),
                }
                read_allowlist.extend((task_ref, submission_ref))
                commands["test"] = (
                    f"llm-lab interview role-test {interview_id} --profile {profile_id}"
                )
            else:
                answer = session["answers"].get(question_id)
                if answer is None:
                    commands["next"] = (
                        f"llm-lab interview role-answer {interview_id} "
                        f"--profile {profile_id} --question {question_id} --file ANSWER_FILE"
                    )
                else:
                    answer_path = _profile_relative(
                        repo_root, profile_id, answer["relative_path"]
                    )
                    answer_ref = _file_ref(
                        repo_root, answer_path, "current_interview_answer"
                    )
                    if answer_ref["sha256"] != answer["sha256"]:
                        raise ContextError("current interview answer changed after recording")
                    current["answer"] = {
                        "path": answer_ref["path"],
                        "sha256": answer_ref["sha256"],
                    }
                    read_allowlist.append(answer_ref)
            if question_id not in session["assessments"] and (
                question_id in session["answers"]
                or question_id in session["coding_evidence"]
            ):
                commands["next"] = (
                    f"llm-lab interview role-score {interview_id} --profile {profile_id} "
                    f"--question {question_id} --help"
                )
            for reference in session["material_refs"]:
                read_allowlist.append(
                    _role_material_ref(repo_root, profile_id, reference)
                )
    else:
        report = (
            profile_paths(repo_root, profile_id).interviews_root
            / interview_id
            / "report.md"
        )
        current = {
            "status": session["status"],
            "result": session["result"],
            "report": None,
        }
        if report.is_file():
            report_ref = _file_ref(repo_root, report, "final_interview_report")
            current["report"] = {
                "path": report_ref["path"],
                "sha256": report_ref["sha256"],
            }
            read_allowlist.append(report_ref)
        commands["next"] = (
            f"llm-lab interview role-report {interview_id} --profile {profile_id}"
        )

    value: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "mode": "INTERVIEWER",
        "profile_id": profile_id,
        "scope": "mock_interview",
        "interview_id": interview_id,
        "policy_refs": _policy_refs(repo_root, "interviewer"),
        "state_fingerprint": "0" * 64,
        "plan_fingerprint": session["plan_fingerprint"],
        "current": current,
        "read_allowlist": read_allowlist,
        "commands": commands,
        "excluded": list(EXCLUDED_CONTEXT),
    }
    return _with_fingerprint(value)


def build_interview_context(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    interview_id: str,
) -> dict[str, Any]:
    """Build a stage-gated context for one explicitly named interview."""

    repo_root = repo_root.resolve()
    if interview_id.startswith(ROLE_INTERVIEW_ID_PREFIX):
        return _build_role_interview_context(
            repo_root, catalog, profile_id, interview_id
        )
    session = load_session(repo_root, profile_id, interview_id, catalog)
    read_allowlist: list[dict[str, str]] = []
    commands: dict[str, str] = {}
    current: dict[str, Any]

    if session["status"] == "ready":
        current = {
            "status": "ready",
            "configuration": session["configuration"],
            "selected_problem": session["selected_problem"],
            "question_plan": [
                {
                    "question_id": item["question_id"],
                    "kind": item["kind"],
                    "timebox_minutes": item["timebox_minutes"],
                }
                for item in session["questions"]
            ],
        }
        commands["next"] = (
            f"llm-lab interview start {interview_id} --profile {profile_id}"
        )
    elif session["status"] == "active":
        stage = current_question(repo_root, profile_id, interview_id, catalog)
        question = stage["question"]
        current = {
            "status": stage["status"],
            "deadline": session["deadline"],
            "question": None,
            "missing_assessments": stage.get("missing_assessments", []),
        }
        if question is not None:
            current_question_view = {
                "question_id": question["question_id"],
                "kind": question["kind"],
                "prompt": question["prompt"],
                "prompt_source": question["prompt_source"],
                "timebox_minutes": question["timebox_minutes"],
            }
            if "problem_id" in question:
                current_question_view["problem_id"] = question["problem_id"]
            current["question"] = current_question_view
            if question["kind"] == "coding":
                problem = catalog.get(question["problem_id"])
                assert problem.problem_dir is not None
                task_ref = _file_ref(
                    repo_root,
                    problem.problem_dir / "task.md",
                    "interview_coding_contract",
                )
                read_allowlist.append(task_ref)
                assert session["coding_submission_relpath"] is not None
                submission, submission_ref = _interview_submission_ref(
                    repo_root,
                    profile_id,
                    interview_id,
                    session["coding_submission_relpath"],
                )
                current["coding"] = {
                    "contract": {"path": task_ref["path"], "sha256": task_ref["sha256"]},
                    "submission": submission,
                }
                read_allowlist.append(submission_ref)
                commands["next"] = (
                    f"llm-lab interview test {interview_id} --profile {profile_id}"
                )
            else:
                if question["prompt_source"] == "fixed":
                    commands["deliver_question"] = (
                        f"llm-lab interview ask {interview_id} --profile {profile_id} "
                        f"--question {question['question_id']} --source ai --file QUESTION_FILE"
                    )
                commands["next"] = (
                    f"llm-lab interview answer {interview_id} --profile {profile_id} "
                    f"--question {question['question_id']} --file ANSWER_FILE"
                )
            for material_id in question["material_ids"]:
                reference = next(
                    (
                        item
                        for item in session["material_refs"]
                        if item["id"] == material_id
                    ),
                    None,
                )
                if reference is None or reference["allowed_use"] != "mock_interview":
                    raise ContextError("current interview question has no matching material consent")
                record = get_material(repo_root, profile_id, material_id)
                if not record.ai_access or record.sha256 != reference["sha256"]:
                    raise ContextError("current interview material consent is stale or revoked")
                material_path = profile_paths(repo_root, profile_id).root.joinpath(
                    *record.relative_path.split("/")
                )
                read_allowlist.append(
                    {
                        "path": _repo_relative(
                            repo_root, material_path, f"material_{material_id}"
                        ),
                        "purpose": "consented_interview_material",
                        "sha256": record.sha256,
                        "material_id": record.id,
                        "allowed_use": reference["allowed_use"],
                    }
                )
        elif stage["status"] in {"awaiting_score", "ready_to_finish"}:
            evidence, evidence_refs = _completed_interview_evidence(
                repo_root, profile_id, session
            )
            current["completed_evidence"] = evidence
            current["rubric"] = session["rubric"]
            read_allowlist.extend(evidence_refs)
            commands["next"] = (
                f"llm-lab interview score {interview_id} --profile {profile_id} --help"
                if stage["status"] == "awaiting_score"
                else f"llm-lab interview finish {interview_id} --profile {profile_id}"
            )
        else:
            commands["next"] = (
                f"llm-lab interview finish {interview_id} --profile {profile_id}"
            )
    else:
        report = (
            profile_paths(repo_root, profile_id).interviews_root
            / interview_id
            / "report.md"
        )
        current = {
            "status": session["status"],
            "result": session["result"],
            "reference_warnings": list(
                reference_warnings(repo_root, profile_id, session, catalog)
            ),
            "report": None,
        }
        if report.is_file():
            report_ref = _file_ref(repo_root, report, "final_interview_report")
            current["report"] = {
                "path": report_ref["path"],
                "sha256": report_ref["sha256"],
            }
            read_allowlist.append(report_ref)
        commands["next"] = (
            f"llm-lab interview report {interview_id} --profile {profile_id}"
        )

    value: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "mode": "INTERVIEWER",
        "profile_id": profile_id,
        "scope": "mock_interview",
        "interview_id": interview_id,
        "policy_refs": _policy_refs(repo_root, "interviewer"),
        "state_fingerprint": "0" * 64,
        "plan_fingerprint": session["plan_fingerprint"],
        "current": current,
        "read_allowlist": read_allowlist,
        "commands": commands,
        "excluded": list(EXCLUDED_CONTEXT),
    }
    return _with_fingerprint(value)
