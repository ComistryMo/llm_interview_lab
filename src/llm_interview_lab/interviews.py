"""Deterministic, profile-local mock interviews over validated Catalog problems."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterable
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

from .catalog import Catalog, CatalogError, Problem, compute_problem_fingerprint
from .grader import GraderResult, run_public_tests
from .materials import MaterialError, get_material
from .submissions import SubmissionError, inspect_submission
from .workspace import WorkspaceError, ensure_profile_is_ignored, load_profile, profile_paths


INTERVIEW_ID_RE = re.compile(r"^interview-[0-9]{4}$")
QUESTION_ID_RE = re.compile(r"^q-[0-9]{3}$")
DIFFICULTY_RANGES = {
    "easy": frozenset({1, 2}),
    "medium": frozenset({2, 3}),
    "hard": frozenset({4, 5}),
}
DURATIONS = frozenset({30, 45, 60, 90})
MODES = frozenset({"catalog", "tailored"})
ASSESSOR_SOURCES = frozenset({"ai", "human", "self"})
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
SUBJECTIVE_DIMENSIONS = (
    "reasoning_complexity",
    "technical_oral",
    "project_evidence",
    "communication",
)
ASSESSMENT_QUESTION_KINDS = {
    "reasoning_complexity": frozenset({"technical_oral", "coding", "follow_up"}),
    "technical_oral": frozenset({"technical_oral", "coding", "follow_up"}),
    "project_evidence": frozenset({"background", "experience"}),
    "communication": frozenset({"introduction", "background", "experience", "technical_oral", "coding", "follow_up"}),
}
RUBRIC_WEIGHTS = {
    "coding_correctness": 30,
    "reasoning_complexity": 20,
    "technical_oral": 20,
    "project_evidence": 15,
    "communication": 10,
    "time_management": 5,
}
TIMEBOXES = {
    30: (3, 5, 7, 15),
    45: (5, 10, 10, 20),
    60: (5, 15, 10, 25, 5),
    90: (5, 20, 15, 40, 10),
}
MAX_ANSWER_BYTES = 1024 * 1024


class InterviewError(RuntimeError):
    """Raised when a mock-interview contract or transition is invalid."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise InterviewError(f"interview session contains duplicate JSON key: {key}")
        value[key] = item
    return value


def _aware_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now().astimezone()
    if current.tzinfo is None or current.utcoffset() is None:
        raise InterviewError("interview clock must include a timezone")
    return current


def _timestamp(value: datetime | None = None) -> str:
    return _aware_now(value).isoformat(timespec="seconds")


def _parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise InterviewError(f"{label} is not a supported ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InterviewError(f"{label} must include a timezone")
    return parsed


def _latest_recorded_time(session: dict[str, Any]) -> datetime:
    values = [_parse_timestamp(session["created_at"], "created_at")]
    if session.get("started_at") is not None:
        values.append(_parse_timestamp(session["started_at"], "started_at"))
    values.extend(
        _parse_timestamp(item["recorded_at"], "answer recorded_at")
        for item in session.get("answers", {}).values()
    )
    evidence = session.get("coding_evidence")
    if evidence is not None:
        values.append(_parse_timestamp(evidence["tested_at"], "coding tested_at"))
    values.extend(
        _parse_timestamp(item["assessed_at"], "assessment assessed_at")
        for item in session.get("assessments", {}).values()
    )
    values.extend(
        _parse_timestamp(item["timestamp"], "timeline timestamp")
        for item in session.get("timeline", [])
    )
    return max(values)


def _mutation_time(session: dict[str, Any], value: datetime | None) -> datetime:
    current = _aware_now(value)
    if session.get("started_at") is not None:
        started_at = _parse_timestamp(session["started_at"], "started_at")
        if current < started_at:
            raise InterviewError("interview clock cannot move before its start time")
    if current < _latest_recorded_time(session):
        raise InterviewError("interview clock cannot move backwards")
    return current


def _schema(repo_root: Path) -> dict[str, Any]:
    try:
        value = json.loads((repo_root / "workspace/schema/interview.schema.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InterviewError("interview schema cannot be read") from error
    if not isinstance(value, dict):
        raise InterviewError("interview schema must be an object")
    return value


def _validate_session(repo_root: Path, session: Any) -> dict[str, Any]:
    if not isinstance(session, dict):
        raise InterviewError("session.json must contain an object")
    errors = sorted(
        Draft202012Validator(_schema(repo_root), format_checker=FormatChecker()).iter_errors(session),
        key=lambda item: list(item.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise InterviewError(f"invalid interview session at {location}: {errors[0].message}")
    question_ids = [item["question_id"] for item in session["questions"]]
    coding = [item for item in session["questions"] if item["kind"] == "coding"]
    material_ids = [item["id"] for item in session["material_refs"]]
    if len(question_ids) != len(set(question_ids)):
        raise InterviewError("interview questions must have unique IDs")
    if len(coding) != 1 or coding[0].get("problem_id") != session["selected_problem"]["problem_id"]:
        raise InterviewError("interview must contain exactly one matching coding question")
    if len(material_ids) != len(set(material_ids)):
        raise InterviewError("interview material references must have unique IDs")
    status = session["status"]
    execution_fields = ("started_at", "deadline", "coding_submission_relpath")
    if status == "ready" and (
        any(session[name] is not None for name in (*execution_fields, "result"))
        or session["answers"]
        or session["coding_evidence"] is not None
        or session["assessments"]
    ):
        raise InterviewError("a ready interview cannot contain execution state")
    if status in {"active", "completed", "incomplete", "timed_out"} and any(
        session[name] is None for name in execution_fields
    ):
        raise InterviewError("a started interview must contain its clock and submission path")
    if status == "active" and session["result"] is not None:
        raise InterviewError("an active interview cannot contain a final result")
    if status in {"completed", "incomplete", "timed_out"} and session["result"] is None:
        raise InterviewError("a finalized interview must contain a result")
    if session["result"] is not None and session["status"] != session["result"]["completion_status"]:
        raise InterviewError("interview status must match its result")
    if status != "ready":
        started_at = _parse_timestamp(session["started_at"], "started_at")
        deadline = _parse_timestamp(session["deadline"], "deadline")
        created_at = _parse_timestamp(session["created_at"], "created_at")
        if started_at < created_at:
            raise InterviewError("interview cannot start before it was created")
        if deadline <= started_at:
            raise InterviewError("interview deadline must be after its start time")
        expected_submission = (
            f"interviews/{session['interview_id']}/coding/submission.py"
        )
        if session["coding_submission_relpath"] != expected_submission:
            raise InterviewError("interview submission path does not match its identity")
        recorded_times = [
            *(
                _parse_timestamp(item["recorded_at"], "answer recorded_at")
                for item in session["answers"].values()
            ),
            *(
                _parse_timestamp(item["assessed_at"], "assessment assessed_at")
                for item in session["assessments"].values()
            ),
        ]
        if session["coding_evidence"] is not None:
            recorded_times.append(
                _parse_timestamp(
                    session["coding_evidence"]["tested_at"], "coding tested_at"
                )
            )
        if any(value < started_at for value in recorded_times):
            raise InterviewError("interview evidence cannot predate its start")
        if session["result"] is not None:
            finished_at = _parse_timestamp(
                session["result"]["finished_at"], "finished_at"
            )
            if finished_at < max(recorded_times, default=started_at):
                raise InterviewError("interview cannot finish before its evidence")

    question_by_id = {item["question_id"]: item for item in session["questions"]}
    for question_id, answer in session["answers"].items():
        question = question_by_id.get(question_id)
        if question is None or question["kind"] == "coding":
            raise InterviewError("answers may reference only known non-coding questions")
        expected_answer = (
            f"interviews/{session['interview_id']}/answers/{question_id}.md"
        )
        if answer["answer_relpath"] != expected_answer:
            raise InterviewError("answer path does not match its question")
    for dimension, assessment in session["assessments"].items():
        if not assessment["question_ids"]:
            raise InterviewError("assessment must reference completed question IDs")
        for question_id in assessment["question_ids"]:
            question = question_by_id.get(question_id)
            if question is None:
                raise InterviewError("assessment references an unknown question ID")
            if question["kind"] not in ASSESSMENT_QUESTION_KINDS[dimension]:
                raise InterviewError("assessment evidence does not match its rubric dimension")
    if (
        session["coding_evidence"] is not None
        and session["coding_evidence"]["problem_id"]
        != session["selected_problem"]["problem_id"]
    ):
        raise InterviewError("coding evidence does not match the selected problem")
    return session


def _is_obvious_link(path: Path) -> bool:
    try:
        value = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(value, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(value.st_mode) or bool(attributes & reparse_flag)


def _reject_linked_components(path: Path, boundary: Path) -> None:
    lexical_path = path.absolute()
    lexical_boundary = boundary.absolute()
    try:
        relative = lexical_path.relative_to(lexical_boundary)
    except ValueError as error:
        raise InterviewError("interview path is outside the current Profile") from error
    current = lexical_boundary
    if _is_obvious_link(current):
        raise InterviewError("interview path must not use a symlink or reparse point")
    for part in relative.parts:
        current = current / part
        if _is_obvious_link(current):
            raise InterviewError("interview path must not use a symlink or reparse point")


def _safe_directory(path: Path, boundary: Path, *, create: bool = False) -> Path:
    _reject_linked_components(path, boundary)
    if not path.exists():
        if not create:
            raise InterviewError("interview directory is missing")
        try:
            path.mkdir()
        except OSError as error:
            raise InterviewError("interview directory cannot be created") from error
    if not path.is_dir() or _is_obvious_link(path):
        raise InterviewError("interview path must be a regular, unlinked directory")
    try:
        path.resolve(strict=True).relative_to(boundary.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise InterviewError("interview directory escapes the current Profile") from error
    return path


def _safe_file(path: Path, boundary: Path) -> Path:
    _reject_linked_components(path, boundary)
    if not path.is_file() or _is_obvious_link(path):
        raise InterviewError("interview evidence file must be a regular, unlinked file")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(boundary.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise InterviewError("interview evidence file escapes the current Profile") from error
    return resolved


def _paths(
    repo_root: Path,
    profile_id: str,
    interview_id: str | None = None,
    *,
    require_ignored: bool = True,
) -> tuple[Path, Path | None]:
    repo_root = repo_root.resolve()
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    if require_ignored:
        try:
            ensure_profile_is_ignored(repo_root, profile_id)
        except WorkspaceError as error:
            raise InterviewError("current Profile is not protected by Git ignore") from error
    profiles_root = repo_root / "workspace/profiles"
    _reject_linked_components(paths.root, profiles_root)
    _safe_directory(paths.root, profiles_root)
    _safe_directory(paths.interviews_root, paths.root, create=require_ignored)
    if interview_id is None:
        return paths.interviews_root, None
    if INTERVIEW_ID_RE.fullmatch(interview_id) is None:
        raise InterviewError("interview ID must use interview-0001 format")
    root = paths.interviews_root / interview_id
    if root.exists() or _is_obvious_link(root):
        _safe_directory(root, paths.interviews_root)
    return root, root / "session.json"


def _atomic_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise InterviewError("interview file cannot be written atomically") from error


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")
    _atomic_bytes(path, encoded)


def _frozen_plan(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "configuration": session["configuration"],
        "material_refs": session["material_refs"],
        "selected_problem": session["selected_problem"],
        "rubric": session["rubric"],
        "questions": session["questions"],
    }


def _plan_fingerprint(session: dict[str, Any]) -> str:
    encoded = json.dumps(_frozen_plan(session), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _write_session(repo_root: Path, path: Path, session: dict[str, Any]) -> None:
    session["plan_fingerprint"] = _plan_fingerprint(session)
    _validate_session(repo_root, session)
    _atomic_json(path, session)


def _problem_allowed(problem: Problem, track_id: str, difficulty: str) -> bool:
    return (
        problem.recommendable
        and not problem.id.startswith("CAP-")
        and track_id in problem.raw["tracks"]
        and problem.raw["difficulty"]["coding"] in DIFFICULTY_RANGES[difficulty]
    )


def _select_problem(
    catalog: Catalog,
    *,
    track_id: str,
    difficulty: str,
    seed: int,
    problem_id: str | None,
) -> Problem:
    if track_id not in catalog.tracks:
        raise InterviewError(f"unknown track: {track_id}")
    if problem_id is not None:
        try:
            problem = catalog.get(problem_id)
        except CatalogError as error:
            raise InterviewError(f"unknown Catalog problem: {problem_id}") from error
        if not _problem_allowed(problem, track_id, difficulty):
            raise InterviewError("selected problem must match the track and difficulty and be Oracle-validated")
        return problem
    candidates = sorted(
        (problem for problem in catalog.problems.values() if _problem_allowed(problem, track_id, difficulty)),
        key=lambda item: item.id,
    )
    if not candidates:
        raise InterviewError("no validated Catalog problem matches the requested track and difficulty")
    identity = f"interview-selection-v1|{track_id}|{difficulty}|{seed}|{'|'.join(item.id for item in candidates)}"
    index = int(hashlib.sha256(identity.encode("utf-8")).hexdigest(), 16) % len(candidates)
    return candidates[index]


def _questions(
    problem: Problem,
    duration_minutes: int,
    tailored: bool,
    focus: str,
) -> list[dict[str, Any]]:
    values = TIMEBOXES[duration_minutes]
    oral = list(problem.raw["assessment"]["oral_questions"])
    questions: list[dict[str, Any]] = [
        {
            "question_id": "q-001",
            "kind": "introduction",
            "prompt": "Give a concise introduction focused on evidence relevant to the selected role.",
            "timebox_minutes": values[0],
            "material_ids": [],
        },
        {
            "question_id": "q-002",
            "kind": "experience" if tailored else "background",
            "prompt": (
                "Use only the consented material IDs to ask for ownership, trade-offs, failures, and measurable evidence."
                + (f" Interview focus: {focus.strip()}" if focus.strip() else "")
                if tailored
                else "Describe one relevant project or learning experience, separating personal contribution from team outcomes."
            ),
            "timebox_minutes": values[1],
            "material_ids": [],
        },
        {
            "question_id": "q-003",
            "kind": "technical_oral",
            "prompt": oral[0],
            "timebox_minutes": values[2],
            "material_ids": [],
        },
        {
            "question_id": "q-004",
            "kind": "coding",
            "prompt": f"Implement {problem.id} {problem.title} under the frozen public contract.",
            "timebox_minutes": values[3],
            "material_ids": [],
            "problem_id": problem.id,
        },
    ]
    if len(values) == 5:
        questions.append(
            {
                "question_id": "q-005",
                "kind": "follow_up",
                "prompt": oral[1],
                "timebox_minutes": values[4],
                "material_ids": [],
            }
        )
    return questions


def _next_id(root: Path) -> str:
    used = {
        int(path.name.split("-")[1])
        for path in root.iterdir()
        if not _is_obvious_link(path)
        and path.is_dir()
        and INTERVIEW_ID_RE.fullmatch(path.name)
    } if root.exists() else set()
    value = 1
    while value in used:
        value += 1
    if value > 9999:
        raise InterviewError("this Profile has reached the interview archive limit")
    return f"interview-{value:04d}"


def create_interview(
    repo_root: Path,
    profile_id: str,
    catalog: Catalog,
    *,
    difficulty: str,
    duration_minutes: int,
    track_id: str,
    mode: str = "catalog",
    material_ids: Iterable[str] = (),
    consent_materials: bool = False,
    problem_id: str | None = None,
    focus: str = "",
    seed: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create and lock one immutable interview plan inside the selected Profile."""

    repo_root = repo_root.resolve()
    if not isinstance(difficulty, str) or difficulty not in DIFFICULTY_RANGES:
        raise InterviewError("difficulty must be easy, medium, or hard")
    if type(duration_minutes) is not int or duration_minutes not in DURATIONS:
        raise InterviewError("duration must be one of 30, 45, 60, or 90 minutes")
    if not isinstance(mode, str) or mode not in MODES:
        raise InterviewError("mode must be catalog or tailored")
    if type(seed) is not int or isinstance(seed, bool) or seed < 0:
        raise InterviewError("seed must be a non-negative integer")
    if isinstance(material_ids, (str, bytes)):
        raise InterviewError("material_ids must be an iterable of material IDs")
    raw_material_ids = tuple(material_ids)
    material_ids = tuple(dict.fromkeys(raw_material_ids))
    if len(material_ids) != len(raw_material_ids):
        raise InterviewError("material IDs must be unique")
    if mode == "tailored" and not material_ids:
        raise InterviewError("tailored interviews require at least one material ID")
    if material_ids and not consent_materials:
        raise InterviewError("selected materials require explicit per-interview consent")
    if mode == "catalog" and material_ids:
        raise InterviewError("catalog mode does not read personal materials; use tailored mode")
    if not isinstance(focus, str) or len(focus) > 500:
        raise InterviewError("focus must be at most 500 characters")

    problem = _select_problem(
        catalog, track_id=track_id, difficulty=difficulty, seed=seed, problem_id=problem_id,
    )
    material_refs: list[dict[str, Any]] = []
    for material_id in material_ids:
        try:
            record = get_material(repo_root, profile_id, material_id)
        except MaterialError as error:
            raise InterviewError(str(error)) from error
        if not record.ai_access:
            raise InterviewError(f"material does not allow AI access: {material_id}")
        material_refs.append({
            "id": record.id,
            "sha256": record.sha256,
            "kind": record.kind,
            "title": record.title,
            "allowed_use": "mock_interview",
        })

    interviews_root, _ = _paths(repo_root, profile_id)
    interview_id = _next_id(interviews_root)
    session_root, session_path = _paths(repo_root, profile_id, interview_id)
    assert session_path is not None
    if session_root.exists() or _is_obvious_link(session_root):
        raise InterviewError("interview directory already exists")
    try:
        session_root.mkdir()
    except OSError as error:
        raise InterviewError("interview directory could not be created") from error
    _safe_directory(session_root, interviews_root)
    questions = _questions(problem, duration_minutes, mode == "tailored", focus)
    for question in questions:
        if question["kind"] == "experience":
            question["material_ids"] = list(material_ids)
    created_at = _timestamp(now)
    session: dict[str, Any] = {
        "schema_version": 1,
        "interview_id": interview_id,
        "profile_id": profile_id,
        "status": "ready",
        "created_at": created_at,
        "configuration": {
            "difficulty": difficulty,
            "duration_minutes": duration_minutes,
            "track_id": track_id,
            "mode": mode,
            "seed": seed,
            "focus": focus.strip(),
        },
        "material_refs": material_refs,
        "selected_problem": {
            "problem_id": problem.id,
            "title": problem.title,
            "validation_level": problem.validation_level,
            "fingerprint": compute_problem_fingerprint(repo_root, problem),
        },
        "rubric": {
            "version": "mixed-v1",
            "weights": RUBRIC_WEIGHTS,
            "score_range": [0, 100],
        },
        "questions": questions,
        "plan_fingerprint": "0" * 64,
        "started_at": None,
        "deadline": None,
        "coding_submission_relpath": None,
        "answers": {},
        "coding_evidence": None,
        "assessments": {},
        "timeline": [{"event": "created", "timestamp": created_at}],
        "result": None,
    }
    try:
        _write_session(repo_root, session_path, session)
    except InterviewError:
        try:
            session_root.rmdir()
        except OSError:
            pass
        raise
    return session


def _reference_warnings(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
    catalog: Catalog | None,
) -> list[str]:
    warnings: list[str] = []
    for reference in session["material_refs"]:
        try:
            material = get_material(repo_root, profile_id, reference["id"])
        except MaterialError as error:
            warnings.append(f"material {reference['id']}: {error}")
            continue
        if material.sha256 != reference["sha256"]:
            warnings.append(f"material {reference['id']}: content changed")
        if not material.ai_access:
            warnings.append(f"material {reference['id']}: AI access revoked")
    if catalog is not None:
        try:
            problem = catalog.get(session["selected_problem"]["problem_id"])
        except CatalogError as error:
            warnings.append(str(error))
        else:
            if not problem.recommendable:
                warnings.append("selected Catalog problem is no longer interview-eligible")
            elif compute_problem_fingerprint(repo_root, problem) != session["selected_problem"]["fingerprint"]:
                warnings.append("selected Catalog problem fingerprint changed")
    if session["result"] is not None:
        for question_id in session["answers"]:
            if not _answer_current(repo_root, profile_id, session, question_id):
                warnings.append(
                    f"answer {question_id}: archived evidence is missing or changed"
                )
        if (
            session["coding_evidence"] is not None
            and not _coding_current(repo_root, profile_id, session)
        ):
            warnings.append("coding submission: archived evidence is missing or changed")
    return warnings


def reference_warnings(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
    catalog: Catalog | None,
) -> tuple[str, ...]:
    """Return non-blocking drift warnings for an archived interview."""

    return tuple(_reference_warnings(repo_root, profile_id, session, catalog))


def _require_current_references(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
    catalog: Catalog | None,
) -> None:
    warnings = _reference_warnings(repo_root, profile_id, session, catalog)
    if warnings:
        raise InterviewError("interview references are stale or revoked: " + "; ".join(warnings))


def load_session(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog | None = None,
    *,
    verify_references: bool = True,
) -> dict[str, Any]:
    root, path = _paths(
        repo_root.resolve(), profile_id, interview_id, require_ignored=False,
    )
    assert path is not None
    if not path.exists() and not _is_obvious_link(path):
        raise InterviewError("interview does not exist for this Profile")
    try:
        safe_path = _safe_file(path, profile_paths(repo_root.resolve(), profile_id).interviews_root)
        session = json.loads(
            safe_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except FileNotFoundError as error:
        raise InterviewError("interview does not exist for this Profile") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InterviewError("interview session cannot be read") from error
    session = _validate_session(repo_root, session)
    if session["profile_id"] != profile_id or session["interview_id"] != interview_id:
        raise InterviewError("interview identity does not match its Profile path")
    if session["plan_fingerprint"] != _plan_fingerprint(session):
        raise InterviewError("interview plan changed after it was locked")
    if verify_references and session["result"] is None:
        _require_current_references(repo_root, profile_id, session, catalog)
    if not root.is_dir():
        raise InterviewError("interview directory is missing")
    return session


def list_interviews(repo_root: Path, profile_id: str, catalog: Catalog | None = None) -> tuple[dict[str, Any], ...]:
    root, _ = _paths(repo_root.resolve(), profile_id, require_ignored=False)
    values: list[dict[str, Any]] = []
    for directory in sorted(root.iterdir()):
        if INTERVIEW_ID_RE.fullmatch(directory.name) is None:
            continue
        if _is_obvious_link(directory) or not directory.is_dir():
            values.append({
                "interview_id": directory.name,
                "status": "unreadable",
                "warnings": ["interview archive path is not a regular, unlinked directory"],
            })
            continue
        try:
            session = load_session(
                repo_root, profile_id, directory.name, catalog, verify_references=False,
            )
        except InterviewError as error:
            values.append({
                "interview_id": directory.name,
                "status": "unreadable",
                "warnings": [str(error)],
            })
            continue
        warnings = _reference_warnings(repo_root, profile_id, session, catalog)
        values.append({
            "interview_id": session["interview_id"],
            "status": session["status"],
            "difficulty": session["configuration"]["difficulty"],
            "duration_minutes": session["configuration"]["duration_minutes"],
            "track_id": session["configuration"]["track_id"],
            "problem_id": session["selected_problem"]["problem_id"],
            "overall_score": session["result"]["overall_score"] if session["result"] else None,
            "warnings": warnings,
        })
    return tuple(values)


def start_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    if session["status"] == "active":
        return session
    if session["status"] != "ready":
        raise InterviewError("only a ready interview can be started")
    current = _aware_now(now)
    if current < _parse_timestamp(session["created_at"], "created_at"):
        raise InterviewError("interview cannot start before it was created")
    root, path = _paths(repo_root.resolve(), profile_id, interview_id)
    assert path is not None
    problem = catalog.get(session["selected_problem"]["problem_id"])
    assert problem.problem_dir is not None
    coding_root = root / "coding"
    submission = coding_root / "submission.py"
    if coding_root.exists() or _is_obvious_link(coding_root):
        raise InterviewError("coding directory already exists without a start event")
    try:
        coding_root.mkdir()
        _safe_directory(coding_root, root)
        starter = (problem.problem_dir / "starter.py").read_bytes()
        _atomic_bytes(submission, starter)
    except (OSError, InterviewError) as error:
        try:
            submission.unlink(missing_ok=True)
            coding_root.rmdir()
        except OSError:
            pass
        if isinstance(error, InterviewError):
            raise
        raise InterviewError("coding starter cannot be copied") from error
    profile_root = profile_paths(repo_root.resolve(), profile_id).root
    started_at = _timestamp(current)
    deadline = _timestamp(current + timedelta(minutes=session["configuration"]["duration_minutes"]))
    session["status"] = "active"
    session["started_at"] = started_at
    session["deadline"] = deadline
    session["coding_submission_relpath"] = submission.relative_to(profile_root).as_posix()
    session["timeline"].append({"event": "started", "timestamp": started_at})
    try:
        _write_session(repo_root, path, session)
    except InterviewError:
        try:
            submission.unlink(missing_ok=True)
            coding_root.rmdir()
        except OSError:
            pass
        raise
    return session


def _remaining(session: dict[str, Any], now: datetime | None) -> int:
    if session["deadline"] is None:
        return session["configuration"]["duration_minutes"] * 60
    deadline = _parse_timestamp(session["deadline"], "deadline")
    current = _mutation_time(session, now)
    return max(0, math.floor((deadline - current).total_seconds()))


def _require_active(session: dict[str, Any]) -> None:
    if session["status"] != "active":
        raise InterviewError("interview is not active")


def _require_time(session: dict[str, Any], now: datetime | None) -> datetime:
    current = _mutation_time(session, now)
    deadline = _parse_timestamp(session["deadline"], "deadline")
    if current >= deadline:
        raise InterviewError("interview time has expired; finish to preserve an incomplete report")
    return current


def _coding_current(repo_root: Path, profile_id: str, session: dict[str, Any]) -> bool:
    evidence = session["coding_evidence"]
    relative = session["coding_submission_relpath"]
    if evidence is None or relative is None:
        return False
    root = profile_paths(repo_root.resolve(), profile_id).root
    try:
        inspected = inspect_submission(root.joinpath(*relative.split("/")), root / f"interviews/{session['interview_id']}/coding")
    except SubmissionError:
        return False
    return (
        evidence["status"] != "internal_error"
        and inspected.sha256 == evidence["submission_sha256"]
    )


def _question_completed(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
    question: dict[str, Any],
) -> bool:
    return (
        _coding_current(repo_root, profile_id, session)
        if question["kind"] == "coding"
        else _answer_current(repo_root, profile_id, session, question["question_id"])
    )


def _next_unanswered_question(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
) -> dict[str, Any] | None:
    return next(
        (
            question
            for question in session["questions"]
            if not _question_completed(repo_root, profile_id, session, question)
        ),
        None,
    )


def current_question(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    _require_active(session)
    remaining = _remaining(session, now)
    question = _next_unanswered_question(repo_root, profile_id, session)
    if remaining == 0 and question is not None:
        return {"status": "expired", "remaining_seconds": 0, "question": None}
    if question is not None:
        return {
            "status": "active",
            "remaining_seconds": remaining,
            "question": question,
            "missing_assessments": [],
        }
    missing = [
        dimension
        for dimension in SUBJECTIVE_DIMENSIONS
        if dimension not in session["assessments"]
    ]
    return {
        "status": "awaiting_score" if missing else "ready_to_finish",
        "remaining_seconds": remaining,
        "question": None,
        "missing_assessments": missing,
    }


def _answer_source(path: Path) -> bytes:
    if path.suffix.lower() not in {".md", ".txt"}:
        raise InterviewError("interview answers must be UTF-8 .md or .txt files")
    try:
        if not path.is_file() or _is_obvious_link(path):
            raise InterviewError("answer path must be a regular non-link file")
        content = path.read_bytes()
        if len(content) > MAX_ANSWER_BYTES:
            raise InterviewError("answer file exceeds 1 MiB")
        text = content.decode("utf-8")
        if not text.strip():
            raise InterviewError("answer file must contain a non-empty answer")
    except UnicodeDecodeError as error:
        raise InterviewError("answer file must be UTF-8") from error
    except OSError as error:
        raise InterviewError("answer file cannot be read") from error
    return content


def _answer_current(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
    question_id: str,
) -> bool:
    answer = session["answers"].get(question_id)
    if answer is None:
        return False
    profile_root = profile_paths(repo_root.resolve(), profile_id).root
    candidate = profile_root.joinpath(*answer["answer_relpath"].split("/"))
    try:
        safe = _safe_file(candidate, profile_root / "interviews")
        content = safe.read_bytes()
        return (
            bool(content.decode("utf-8").strip())
            and hashlib.sha256(content).hexdigest() == answer["sha256"]
        )
    except (InterviewError, OSError, UnicodeError):
        return False


def record_answer(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    question_id: str,
    answer_path: Path,
    *,
    asked_question: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    _require_active(session)
    action_time = _require_time(session, now)
    question = next((item for item in session["questions"] if item["question_id"] == question_id), None)
    if question is None:
        raise InterviewError("unknown interview question ID")
    if question["kind"] == "coding":
        raise InterviewError("coding answers are recorded by the interview test command")
    current = _next_unanswered_question(repo_root, profile_id, session)
    if current is None or current["question_id"] != question_id:
        raise InterviewError("answer the current interview question before later questions")
    content = _answer_source(answer_path)
    digest = hashlib.sha256(content).hexdigest()
    existing = session["answers"].get(question_id)
    if existing:
        if existing["sha256"] == digest and _answer_current(
            repo_root, profile_id, session, question_id,
        ):
            return session
        raise InterviewError("question already has a different recorded answer")
    if asked_question is not None and (
        not isinstance(asked_question, str)
        or not asked_question.strip()
        or len(asked_question) > 2000
    ):
        raise InterviewError("asked question must contain 1 to 2000 characters")
    root, path = _paths(repo_root.resolve(), profile_id, interview_id)
    assert path is not None
    target = root / "answers" / f"{question_id}.md"
    answers_root = target.parent
    try:
        if not answers_root.exists():
            answers_root.mkdir()
        _safe_directory(answers_root, root)
        if target.exists() or _is_obvious_link(target):
            raise InterviewError("answer evidence path already exists")
        _atomic_bytes(target, content)
    except OSError as error:
        raise InterviewError("answer cannot be stored") from error
    profile_root = profile_paths(repo_root.resolve(), profile_id).root
    recorded_at = _timestamp(action_time)
    session["answers"][question_id] = {
        "answer_relpath": target.relative_to(profile_root).as_posix(),
        "sha256": digest,
        "recorded_at": recorded_at,
        "asked_question": asked_question.strip() if asked_question else question["prompt"],
    }
    session["timeline"].append({"event": "answer_recorded", "timestamp": recorded_at, "question_id": question_id})
    try:
        _write_session(repo_root, path, session)
    except InterviewError:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return session


def run_coding_test(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    now: datetime | None = None,
) -> GraderResult:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    _require_active(session)
    action_time = _require_time(session, now)
    problem = catalog.get(session["selected_problem"]["problem_id"])
    assert problem.public_tests is not None and problem.symbol is not None
    root, path = _paths(repo_root.resolve(), profile_id, interview_id)
    assert path is not None and session["coding_submission_relpath"] is not None
    profile_root = profile_paths(repo_root.resolve(), profile_id).root
    submission = profile_root.joinpath(*session["coding_submission_relpath"].split("/"))
    current = _next_unanswered_question(repo_root, profile_id, session)
    if current is None or current["kind"] != "coding":
        raise InterviewError("the coding question is not current")
    result = run_public_tests(
        repo_root=repo_root,
        test_path=problem.public_tests,
        submission_path=submission,
        submissions_root=root / "coding",
        expected_symbol=problem.symbol,
        time_limit_ms=problem.time_limit_ms,
        output_limit_kb=problem.output_limit_kb,
    )
    tested_at = _timestamp(action_time)
    session["coding_evidence"] = {
        "problem_id": problem.id,
        "submission_sha256": result.submission_sha256,
        "status": result.status,
        "passed": result.passed,
        "failed": result.failed,
        "duration_ms": result.duration_ms,
        "output_truncated": result.output_truncated,
        "tested_at": tested_at,
    }
    session["timeline"].append({"event": "coding_tested", "timestamp": tested_at, "question_id": "q-004"})
    _write_session(repo_root, path, session)
    return result


def record_assessment(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    dimension: str,
    score: float,
    source: str,
    evidence: str,
    confidence: str,
    *,
    question_ids: Iterable[str] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    _require_active(session)
    if dimension not in SUBJECTIVE_DIMENSIONS:
        raise InterviewError("only subjective rubric dimensions can be assessor-scored")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or not 0 <= float(score) <= 100:
        raise InterviewError("assessment score must be a finite number from 0 to 100")
    if source not in ASSESSOR_SOURCES:
        raise InterviewError("assessment source must be ai, human, or self")
    if confidence not in CONFIDENCE_LEVELS:
        raise InterviewError("confidence must be low, medium, or high")
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 4000:
        raise InterviewError("assessment evidence must contain 1 to 4000 characters")
    question_ids = tuple(dict.fromkeys(question_ids))
    known = {item["question_id"] for item in session["questions"]}
    if not question_ids:
        raise InterviewError("assessment must reference at least one completed question ID")
    if set(question_ids) - known:
        raise InterviewError("assessment references an unknown question ID")
    question_by_id = {item["question_id"]: item for item in session["questions"]}
    if any(
        not _question_completed(repo_root, profile_id, session, question_by_id[question_id])
        for question_id in question_ids
    ):
        raise InterviewError("assessment can reference only completed interview questions")
    if any(
        question_by_id[question_id]["kind"] not in ASSESSMENT_QUESTION_KINDS[dimension]
        for question_id in question_ids
    ):
        raise InterviewError("assessment question evidence does not match the rubric dimension")
    semantic_record = {
        "score": round(float(score), 1),
        "source": source,
        "evidence": evidence.strip(),
        "confidence": confidence,
        "question_ids": list(question_ids),
    }
    existing = session["assessments"].get(dimension)
    if existing is not None:
        if all(existing[key] == value for key, value in semantic_record.items()):
            return session
        raise InterviewError("assessment dimension is already recorded and cannot be replaced")
    assessed_at = _timestamp(_mutation_time(session, now))
    record = {**semantic_record, "assessed_at": assessed_at}
    session["assessments"][dimension] = record
    session["timeline"].append({"event": "assessment_recorded", "timestamp": assessed_at, "dimension": dimension})
    _, path = _paths(repo_root.resolve(), profile_id, interview_id)
    assert path is not None
    _write_session(repo_root, path, session)
    return session


def _coding_score(session: dict[str, Any], current: bool) -> float:
    evidence = session["coding_evidence"]
    if evidence is None or not current:
        return 0.0
    if evidence["status"] == "passed":
        return 100.0
    # Public-test counts do not encode collection/runtime errors precisely.
    # A non-passing run is conservative evidence, not a fractional oracle.
    return 0.0


def _all_candidate_questions_answered(repo_root: Path, profile_id: str, session: dict[str, Any]) -> bool:
    return _next_unanswered_question(repo_root, profile_id, session) is None


def _elapsed_seconds(
    session: dict[str, Any],
    finished_at: datetime,
    *,
    candidate_complete: bool,
) -> int:
    started_at = _parse_timestamp(session["started_at"], "started_at")
    candidate_times = [
        _parse_timestamp(answer["recorded_at"], "answer recorded_at")
        for answer in session["answers"].values()
    ]
    if session["coding_evidence"] is not None:
        candidate_times.append(
            _parse_timestamp(
                session["coding_evidence"]["tested_at"], "coding tested_at"
            )
        )
    endpoint = (
        max(candidate_times)
        if candidate_complete and candidate_times
        else finished_at
    )
    return max(0, math.floor((endpoint - started_at).total_seconds()))


def _candidate_within_deadline(session: dict[str, Any]) -> bool:
    if not session["answers"] or session["coding_evidence"] is None:
        return False
    deadline = _parse_timestamp(session["deadline"], "deadline")
    timestamps = [
        _parse_timestamp(answer["recorded_at"], "answer recorded_at")
        for answer in session["answers"].values()
    ]
    timestamps.append(
        _parse_timestamp(
            session["coding_evidence"]["tested_at"], "coding tested_at"
        )
    )
    return max(timestamps) <= deadline


def _render_report(
    session: dict[str, Any], reference_drift: Iterable[str] = ()
) -> str:
    result = session["result"]
    assert result is not None
    lines = [
        f"# Mock Interview Report — {session['interview_id']}",
        "",
        f"- Status: `{result['completion_status']}`",
        f"- Track: `{session['configuration']['track_id']}`",
        f"- Difficulty: `{session['configuration']['difficulty']}`",
        f"- Planned duration: {session['configuration']['duration_minutes']} minutes",
        f"- Catalog problem: `{session['selected_problem']['problem_id']}` {session['selected_problem']['title']}",
        (
            f"- Overall score: **{result['overall_score']:.1f} / 100**"
            if result["completion_status"] == "completed"
            else f"- Partial evidence score: **{result['overall_score']:.1f} / 100** (not a complete interview score)"
        ),
        f"- Candidate elapsed time: {result['elapsed_seconds']} seconds",
        f"- Outcome: **{result['outcome']}**",
    ]
    warnings = tuple(reference_drift)
    if warnings:
        lines.extend([
            "",
            "## Archive reference warnings",
            "",
            *(f"- {html.escape(warning)}" for warning in warnings),
        ])
    lines.extend([
        "",
        "## Objective and subjective evidence",
        "",
        "| Dimension | Weight | Score | Source |",
        "| --- | ---: | ---: | --- |",
    ])
    for dimension, weight in session["rubric"]["weights"].items():
        detail = result["dimensions"][dimension]
        lines.append(f"| `{dimension}` | {weight} | {detail['score']:.1f} | {detail['source']} |")
    lines.extend(["", "### Evidence details", ""])
    for dimension in session["rubric"]["weights"]:
        detail = result["dimensions"][dimension]
        references = ", ".join(detail["question_ids"]) or "session"
        evidence = " ".join(detail["evidence"].splitlines())
        lines.append(
            f"- `{dimension}` ({detail['confidence']}; {references}): "
            f"<code>{html.escape(evidence)}</code>"
        )
    lines.extend([
        "",
        "## Summary",
        "",
        f"<pre>{html.escape(result['summary'])}</pre>",
        "",
        "## Strengths",
        "",
        *(f"- `{value}`" for value in result["strengths"]),
        "",
        "## Gaps",
        "",
        *(f"- `{value}`" for value in result["gaps"]),
        "",
        "## Recommended practice",
        "",
        *(f"- `{value}`" for value in result["recommended_problem_ids"]),
        "",
        "> This is evidence from a local mock interview, not an employment probability, mastery decision, or security assessment.",
        "",
    ])
    return "\n".join(lines)


def _write_report(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    session: dict[str, Any],
    reference_drift: Iterable[str] = (),
) -> None:
    root, _ = _paths(repo_root.resolve(), profile_id, interview_id)
    report = root / "report.md"
    if _is_obvious_link(report) or (report.exists() and not report.is_file()):
        raise InterviewError("report path must be a regular, unlinked file")
    _reject_linked_components(report, root)
    _atomic_bytes(
        report, _render_report(session, reference_drift).encode("utf-8")
    )


def finish_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    summary: str = "",
    confirm_incomplete: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_session(repo_root, profile_id, interview_id, catalog)
    if session["result"] is not None:
        _write_report(
            repo_root,
            profile_id,
            interview_id,
            session,
            reference_warnings(repo_root, profile_id, session, catalog),
        )
        return session
    _require_active(session)
    if not isinstance(summary, str) or len(summary) > 4000:
        raise InterviewError("summary must be at most 4000 characters")
    current_code = _coding_current(repo_root, profile_id, session)
    candidate_complete = _all_candidate_questions_answered(repo_root, profile_id, session)
    assessments_complete = all(dimension in session["assessments"] for dimension in SUBJECTIVE_DIMENSIONS)
    evidence_complete = candidate_complete and current_code and assessments_complete
    finished_at = _mutation_time(session, now)
    deadline = _parse_timestamp(session["deadline"], "deadline")
    # Assessor scoring may happen after the candidate timebox. Candidate answers
    # and code tests are already rejected at/after the deadline, so their
    # completeness is the authoritative time-management evidence.
    candidate_within_time = candidate_complete and _candidate_within_deadline(session)
    if not evidence_complete and finished_at <= deadline and not confirm_incomplete:
        raise InterviewError(
            "interview evidence is incomplete before the deadline; pass --confirm-incomplete to finalize early"
        )
    if candidate_complete:
        completion_status = (
            "timed_out"
            if not candidate_within_time
            else "completed"
            if evidence_complete
            else "incomplete"
        )
    else:
        completion_status = "timed_out" if finished_at > deadline else "incomplete"

    dimensions: dict[str, dict[str, Any]] = {
        "coding_correctness": {
            "score": _coding_score(session, current_code),
            "source": "grader",
            "evidence": "current-SHA public test result" if current_code else "missing or stale public test result",
            "confidence": "high",
            "question_ids": ["q-004"],
        },
        "time_management": {
            "score": 100.0 if candidate_within_time else 0.0,
            "source": "session_clock",
            "evidence": "candidate evidence completed within the local deadline" if candidate_within_time else "deadline or completion requirement not met",
            "confidence": "high",
            "question_ids": [item["question_id"] for item in session["questions"]],
        },
    }
    for dimension in SUBJECTIVE_DIMENSIONS:
        assessment = session["assessments"].get(dimension)
        dimensions[dimension] = {
            "score": assessment["score"] if assessment else 0.0,
            "source": assessment["source"] if assessment else "unscored",
            "evidence": assessment["evidence"] if assessment else "required evidence missing",
            "confidence": assessment["confidence"] if assessment else "none",
            "question_ids": assessment["question_ids"] if assessment else [],
        }
    overall = round(sum(dimensions[name]["score"] * weight / 100 for name, weight in RUBRIC_WEIGHTS.items()), 1)
    if not evidence_complete:
        outcome = "Insufficient evidence"
    elif overall >= 85:
        outcome = "Strong"
    elif overall >= 70:
        outcome = "On track"
    elif overall >= 60:
        outcome = "Needs focused practice"
    else:
        outcome = "Needs practice"
    ranked = sorted(dimensions, key=lambda name: dimensions[name]["score"], reverse=True)
    problem_id = session["selected_problem"]["problem_id"]
    problem = catalog.get(problem_id)
    recommendations = [problem_id, *problem.prerequisites] if overall < 80 else []
    result = {
        "completion_status": completion_status,
        "evidence_status": "complete" if evidence_complete else "partial",
        "finished_at": _timestamp(finished_at),
        "elapsed_seconds": _elapsed_seconds(
            session, finished_at, candidate_complete=candidate_complete
        ),
        "overall_score": overall,
        "outcome": outcome,
        "dimensions": dimensions,
        "strengths": ranked[:2],
        "gaps": ranked[-2:],
        "recommended_problem_ids": list(dict.fromkeys(recommendations)),
        "summary": summary.strip() or "Deterministic aggregation completed; review the evidence-separated dimensions below.",
        "mastery_changed": False,
    }
    session["result"] = result
    session["status"] = completion_status
    session["timeline"].append({"event": "finished", "timestamp": result["finished_at"]})
    _, path = _paths(repo_root.resolve(), profile_id, interview_id)
    assert path is not None
    _write_session(repo_root, path, session)
    try:
        _write_report(repo_root, profile_id, interview_id, session)
    except InterviewError as error:
        raise InterviewError("interview was finalized but report.md could not be generated") from error
    return session


def report_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    format_name: str = "markdown",
) -> str:
    session = load_session(
        repo_root, profile_id, interview_id, catalog, verify_references=False,
    )
    if session["result"] is None:
        raise InterviewError("interview has not been finalized")
    warnings = reference_warnings(repo_root, profile_id, session, catalog)
    if format_name == "json":
        value = {**session["result"], "reference_warnings": list(warnings)}
        return json.dumps(value, ensure_ascii=False, indent=2)
    if format_name != "markdown":
        raise InterviewError("report format must be markdown or json")
    _write_report(repo_root, profile_id, interview_id, session, warnings)
    return _render_report(session, warnings)
