"""Deterministic, profile-local interviews driven by public role blueprints.

The engine freezes public questions and scoring contracts, while answers and
reports remain inside one ignored Profile.  It deliberately does not call an
LLM: a human interviewer or an optional AI client may deliver follow-ups and
record rubric evidence through this API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

import yaml
from jsonschema import Draft202012Validator

from .catalog import Catalog, Problem, compute_problem_fingerprint
from .grader import GraderResult, run_public_tests
from .materials import MaterialError, get_material
from .roles import InterviewItem, RoleCatalog
from .workspace import (
    WorkspaceError,
    ensure_profile_is_ignored,
    ensure_profile_path_is_safe,
    load_profile,
    profile_paths,
)


ROLE_INTERVIEW_ID_PREFIX = "role-interview-"
ROLE_INTERVIEW_ID_WIDTH = 4
DIFFICULTY_BANDS = {
    "easy": frozenset({1, 2}),
    "medium": frozenset({2, 3, 4}),
    "hard": frozenset({4, 5}),
}
ASSESSOR_SOURCES = frozenset({"human", "ai", "self"})
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})


class RoleInterviewError(RuntimeError):
    """Raised when a role-aware interview contract would be violated."""


def _timestamp(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise RoleInterviewError("interview timestamps must be timezone-aware")
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise RoleInterviewError("interview timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RoleInterviewError("interview timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _session_schema(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "workspace/schema/role-interview-session.schema.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RoleInterviewError("role interview schema cannot be read") from error
    if not isinstance(value, dict):
        raise RoleInterviewError("role interview schema must be an object")
    return value


def _validate(repo_root: Path, session: Any) -> dict[str, Any]:
    if not isinstance(session, dict):
        raise RoleInterviewError("role interview session must be an object")
    errors = sorted(
        Draft202012Validator(_session_schema(repo_root)).iter_errors(session),
        key=lambda item: list(item.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise RoleInterviewError(
            f"invalid role interview session at {location}: {errors[0].message}"
        )
    return session


def _session_root(repo_root: Path, profile_id: str, interview_id: str) -> Path:
    if not (
        interview_id.startswith(ROLE_INTERVIEW_ID_PREFIX)
        and len(interview_id) == len(ROLE_INTERVIEW_ID_PREFIX) + ROLE_INTERVIEW_ID_WIDTH
        and interview_id[-ROLE_INTERVIEW_ID_WIDTH:].isdigit()
    ):
        raise RoleInterviewError("role interview ID must use role-interview-0001 format")
    paths = profile_paths(repo_root, profile_id)
    return ensure_profile_path_is_safe(
        repo_root, profile_id, paths.interviews_root / interview_id
    )


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise RoleInterviewError("role interview file could not be written") from error


def _plan_value(session: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role_id": session["role_id"],
        "seniority": session["seniority"],
        "difficulty": session["difficulty"],
        "blueprint_id": session["blueprint_id"],
        "duration_minutes": session["duration_minutes"],
        "ai_mode": session["ai_mode"],
        "material_refs": session["material_refs"],
        "questions": session["questions"],
    }


def _plan_fingerprint(session: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _plan_value(session), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_session(repo_root: Path, path: Path, session: dict[str, Any]) -> None:
    session["plan_fingerprint"] = _plan_fingerprint(session)
    _validate(repo_root, session)
    _atomic_write(
        path,
        (json.dumps(session, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def _next_id(interviews_root: Path) -> str:
    used: set[int] = set()
    for path in interviews_root.iterdir():
        if path.is_dir() and path.name.startswith(ROLE_INTERVIEW_ID_PREFIX):
            suffix = path.name[len(ROLE_INTERVIEW_ID_PREFIX) :]
            if len(suffix) == ROLE_INTERVIEW_ID_WIDTH and suffix.isdigit():
                used.add(int(suffix))
    number = 1
    while number in used:
        number += 1
    if number > 9999:
        raise RoleInterviewError("this Profile has reached the role interview limit")
    return f"{ROLE_INTERVIEW_ID_PREFIX}{number:04d}"


def _stable_choice(values: tuple[Any, ...], identity: str) -> Any:
    if not values:
        raise RoleInterviewError("interview blueprint has no eligible fixed item")
    index = int(hashlib.sha256(identity.encode("utf-8")).hexdigest(), 16) % len(values)
    return values[index]


def _coding_candidates(
    catalog: Catalog, track_ids: tuple[str, ...], difficulty: str
) -> tuple[Problem, ...]:
    band = DIFFICULTY_BANDS[difficulty]
    tracks = set(track_ids)
    return tuple(
        sorted(
            (
                problem
                for problem in catalog.problems.values()
                if problem.recommendable
                and not problem.id.startswith("CAP-")
                and tracks.intersection(problem.raw["tracks"])
                and problem.raw["difficulty"]["coding"] in band
            ),
            key=lambda problem: problem.id,
        )
    )


def _item_question(
    item: InterviewItem,
    *,
    question_id: str,
    round_index: int,
    round_weight: float,
    timebox_minutes: int,
) -> dict[str, Any]:
    task = item.task_path.read_bytes()
    loaded_rubric = yaml.safe_load(item.rubric_path.read_text(encoding="utf-8"))
    rubric = {
        "dimensions": {
            name: {
                "weight": value["weight"],
                "anchors": {str(anchor): text for anchor, text in value["anchors"].items()},
            }
            for name, value in loaded_rubric["dimensions"].items()
        },
        "fatal_issues": list(loaded_rubric["fatal_issues"]),
    }
    return {
        "question_id": question_id,
        "round_index": round_index,
        "kind": item.kind,
        "title": item.title,
        "timebox_minutes": timebox_minutes,
        "round_weight": round_weight,
        "skills": list(item.skills),
        "source": {
            "kind": "fixed_item",
            "id": item.id,
            "sha256": hashlib.sha256(task).hexdigest(),
        },
        "prompt": task.decode("utf-8"),
        "rubric": rubric,
    }


def _coding_question(
    repo_root: Path,
    problem: Problem,
    *,
    question_id: str,
    round_index: int,
    round_weight: float,
    timebox_minutes: int,
    skills: tuple[str, ...],
) -> dict[str, Any]:
    assert problem.problem_dir is not None
    task = (problem.problem_dir / "task.md").read_bytes()
    return {
        "question_id": question_id,
        "round_index": round_index,
        "kind": "coding",
        "title": f"{problem.id} {problem.title}",
        "timebox_minutes": timebox_minutes,
        "round_weight": round_weight,
        "skills": list(skills or problem.canonical_skills),
        "source": {
            "kind": "catalog_problem",
            "id": problem.id,
            "sha256": compute_problem_fingerprint(repo_root, problem),
        },
        "prompt": task.decode("utf-8"),
        "rubric": {
            "dimensions": {
                "correctness": {
                    "weight": 1.0,
                    "anchors": {
                        "1": "Public tests do not pass and the contract is not met.",
                        "3": "The approach is plausible but evidence is incomplete.",
                        "5": "The frozen public tests pass under the stated contract.",
                    },
                }
            },
            "fatal_issues": ["does_not_run", "changes_contract"],
        },
    }


def create_role_interview(
    repo_root: Path,
    profile_id: str,
    catalog: Catalog,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str = "new_grad",
    difficulty: str = "medium",
    ai_mode: str = "disabled",
    material_ids: Iterable[str] = (),
    consent_materials: bool = False,
    seed: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Freeze one role blueprint without starting its clock."""

    repo_root = repo_root.resolve()
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    ensure_profile_is_ignored(repo_root, profile_id)
    if difficulty not in DIFFICULTY_BANDS:
        raise RoleInterviewError("difficulty must be easy, medium, or hard")
    if ai_mode not in {"disabled", "provider", "codex"}:
        raise RoleInterviewError("AI mode must be disabled, provider, or codex")
    if type(seed) is not int or isinstance(seed, bool) or seed < 0:
        raise RoleInterviewError("seed must be a non-negative integer")
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)

    selected_materials = tuple(dict.fromkeys(material_ids))
    if selected_materials and not consent_materials:
        raise RoleInterviewError("materials require explicit per-interview consent")
    material_refs: list[dict[str, Any]] = []
    for material_id in selected_materials:
        try:
            material = get_material(repo_root, profile_id, material_id)
        except MaterialError as error:
            raise RoleInterviewError(str(error)) from error
        if not material.ai_access:
            raise RoleInterviewError(f"material does not allow AI access: {material.id}")
        material_refs.append(
            {
                "id": material.id,
                "sha256": material.sha256,
                "kind": material.kind,
                "title": material.title,
                "allowed_use": "role_interview",
            }
        )

    questions: list[dict[str, Any]] = []
    used_items: set[str] = set()
    used_problems: set[str] = set()
    coding_pool = _coding_candidates(catalog, role.required_tracks, difficulty)
    number = 1
    for round_index, round_value in enumerate(blueprint.rounds):
        each_timebox = max(1, round_value.duration // round_value.item_count)
        for item_index in range(round_value.item_count):
            question_id = f"q-{number:03d}"
            identity = (
                f"role-interview-v1|{role.id}|{seniority}|{difficulty}|{seed}|"
                f"{round_index}|{item_index}"
            )
            if round_value.type == "coding":
                available = tuple(p for p in coding_pool if p.id not in used_problems)
                problem = _stable_choice(available or coding_pool, identity)
                used_problems.add(problem.id)
                question = _coding_question(
                    repo_root,
                    problem,
                    question_id=question_id,
                    round_index=round_index,
                    round_weight=round_value.weight,
                    timebox_minutes=each_timebox,
                    skills=round_value.skills,
                )
            else:
                pool = tuple(
                    item
                    for item in role_catalog.eligible_items(
                        role.id, seniority, round_value.type, round_value.skills
                    )
                    if item.id not in used_items
                    and item.difficulty in DIFFICULTY_BANDS[difficulty]
                )
                if not pool:
                    pool = tuple(
                        item
                        for item in role_catalog.eligible_items(
                            role.id, seniority, round_value.type, round_value.skills
                        )
                        if item.id not in used_items
                    )
                item = _stable_choice(pool, identity)
                used_items.add(item.id)
                question = _item_question(
                    item,
                    question_id=question_id,
                    round_index=round_index,
                    round_weight=round_value.weight,
                    timebox_minutes=each_timebox,
                )
            questions.append(question)
            number += 1

    paths.interviews_root.mkdir(exist_ok=True)
    interview_id = _next_id(paths.interviews_root)
    root = _session_root(repo_root, profile_id, interview_id)
    root.mkdir()
    (root / "answers").mkdir()
    (root / "coding").mkdir()
    created_at = _timestamp(now)
    session: dict[str, Any] = {
        "schema_version": 1,
        "interview_id": interview_id,
        "profile_id": profile_id,
        "status": "ready",
        "created_at": created_at,
        "role_id": role.id,
        "seniority": seniority,
        "difficulty": difficulty,
        "blueprint_id": blueprint.id,
        "duration_minutes": blueprint.duration_minutes,
        "ai_mode": ai_mode,
        "material_refs": material_refs,
        "questions": questions,
        "plan_fingerprint": "0" * 64,
        "started_at": None,
        "deadline": None,
        "answers": {},
        "coding_evidence": {},
        "assessments": {},
        "followups": [],
        "timeline": [{"event": "created", "timestamp": created_at}],
        "result": None,
    }
    try:
        _write_session(repo_root, root / "session.json", session)
    except Exception:
        for child in (root / "answers", root / "coding"):
            child.rmdir()
        root.rmdir()
        raise
    return session


def load_role_interview(
    repo_root: Path, profile_id: str, interview_id: str
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    try:
        root = _session_root(repo_root, profile_id, interview_id)
        path = ensure_profile_path_is_safe(
            repo_root, profile_id, root / "session.json", must_exist=True
        )
    except WorkspaceError as error:
        raise RoleInterviewError("role interview does not exist for this Profile") from error
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RoleInterviewError("role interview session cannot be read") from error
    session = _validate(repo_root, session)
    if session["interview_id"] != interview_id or session["profile_id"] != profile_id:
        raise RoleInterviewError("role interview identity does not match its Profile")
    if session["plan_fingerprint"] != _plan_fingerprint(session):
        raise RoleInterviewError("role interview plan changed after it was frozen")
    return session


def _save(repo_root: Path, profile_id: str, session: dict[str, Any]) -> None:
    root = _session_root(repo_root, profile_id, session["interview_id"])
    _write_session(repo_root, root / "session.json", session)


def start_role_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "ready":
        raise RoleInterviewError("only a ready interview can be started")
    current = _parse_timestamp(_timestamp(now))
    root = _session_root(repo_root, profile_id, interview_id)
    for question in session["questions"]:
        if question["kind"] != "coding":
            continue
        problem = catalog.get(question["source"]["id"])
        if compute_problem_fingerprint(repo_root, problem) != question["source"]["sha256"]:
            raise RoleInterviewError("coding problem changed after the interview was planned")
        assert problem.problem_dir is not None
        target_root = root / "coding" / question["question_id"]
        target_root.mkdir()
        (target_root / "submission.py").write_bytes(
            (problem.problem_dir / "starter.py").read_bytes()
        )
    session["status"] = "active"
    session["started_at"] = _timestamp(current)
    session["deadline"] = _timestamp(
        current + timedelta(minutes=session["duration_minutes"])
    )
    session["timeline"].append({"event": "started", "timestamp": _timestamp(current)})
    _save(repo_root, profile_id, session)
    return session


def _remaining_seconds(session: Mapping[str, Any], now: datetime | None = None) -> int:
    if session["deadline"] is None:
        return session["duration_minutes"] * 60
    return max(
        0,
        int(
            (
                _parse_timestamp(session["deadline"])
                - _parse_timestamp(_timestamp(now))
            ).total_seconds()
        ),
    )


def _has_response(session: Mapping[str, Any], question: Mapping[str, Any]) -> bool:
    question_id = question["question_id"]
    if question["kind"] == "coding":
        return question_id in session["coding_evidence"]
    return question_id in session["answers"]


def _is_complete(session: Mapping[str, Any], question: Mapping[str, Any]) -> bool:
    """A question advances only after response evidence and assessment exist."""

    question_id = question["question_id"]
    return _has_response(session, question) and question_id in session["assessments"]


def current_role_question(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "active":
        raise RoleInterviewError("role interview is not active")
    remaining = _remaining_seconds(session, now)
    if remaining == 0:
        raise RoleInterviewError("role interview time has expired; finish it as incomplete")
    question = next(
        (value for value in session["questions"] if not _is_complete(session, value)),
        None,
    )
    return {"question": question, "remaining_seconds": remaining}


def record_role_answer(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    question_id: str,
    answer: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 50_000:
        raise RoleInterviewError("answer must contain 1 to 50000 characters")
    session = load_role_interview(repo_root, profile_id, interview_id)
    current = current_role_question(repo_root, profile_id, interview_id, now=now)["question"]
    if current is None or current["question_id"] != question_id:
        raise RoleInterviewError("only the current question may be answered")
    if current["kind"] == "coding":
        raise RoleInterviewError("run the coding grader instead of recording a text answer")
    if question_id in session["answers"]:
        raise RoleInterviewError("the current question already has recorded answer evidence")
    root = _session_root(repo_root, profile_id, interview_id)
    path = ensure_profile_path_is_safe(
        repo_root, profile_id, root / "answers" / f"{question_id}.md"
    )
    content = answer.strip().encode("utf-8")
    _atomic_write(path, content + b"\n")
    recorded_at = _timestamp(now)
    session["answers"][question_id] = {
        "relative_path": path.relative_to(profile_paths(repo_root, profile_id).root).as_posix(),
        "sha256": hashlib.sha256(content + b"\n").hexdigest(),
        "recorded_at": recorded_at,
    }
    session["timeline"].append(
        {"event": "answered", "question_id": question_id, "timestamp": recorded_at}
    )
    _save(repo_root, profile_id, session)
    return session


def run_role_coding_test(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    catalog: Catalog,
    *,
    now: datetime | None = None,
) -> GraderResult:
    session = load_role_interview(repo_root, profile_id, interview_id)
    current = current_role_question(repo_root, profile_id, interview_id, now=now)["question"]
    if current is None or current["kind"] != "coding":
        raise RoleInterviewError("the current question is not coding")
    problem = catalog.get(current["source"]["id"])
    if compute_problem_fingerprint(repo_root, problem) != current["source"]["sha256"]:
        raise RoleInterviewError("coding problem changed after the interview was planned")
    assert problem.public_tests is not None and problem.symbol is not None
    root = _session_root(repo_root, profile_id, interview_id)
    submission_root = root / "coding" / current["question_id"]
    result = run_public_tests(
        repo_root=repo_root,
        test_path=problem.public_tests,
        submission_path=submission_root / "submission.py",
        submissions_root=submission_root,
        expected_symbol=problem.symbol,
        time_limit_ms=problem.time_limit_ms,
        output_limit_kb=problem.output_limit_kb,
    )
    recorded_at = _timestamp(now)
    session["coding_evidence"][current["question_id"]] = {
        "submission_sha256": result.submission_sha256,
        "status": result.status,
        "passed": result.passed,
        "failed": result.failed,
        "duration_ms": result.duration_ms,
        "recorded_at": recorded_at,
    }
    session["timeline"].append(
        {
            "event": "coding_tested",
            "question_id": current["question_id"],
            "timestamp": recorded_at,
        }
    )
    _save(repo_root, profile_id, session)
    return result


def record_role_followup(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    parent_question_id: str,
    prompt: str,
    answer: str,
    source: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Archive one adaptive follow-up without altering the frozen main plan."""

    if source not in {"human", "ai"}:
        raise RoleInterviewError("follow-up source must be human or ai")
    if not prompt.strip() or not answer.strip() or len(prompt) > 4000 or len(answer) > 20_000:
        raise RoleInterviewError("follow-up prompt or answer is empty or too long")
    session = load_role_interview(repo_root, profile_id, interview_id)
    if parent_question_id not in session["answers"]:
        raise RoleInterviewError("follow-up requires an answered primary question")
    session["followups"].append(
        {
            "followup_id": f"f-{len(session['followups']) + 1:03d}",
            "parent_question_id": parent_question_id,
            "prompt": prompt.strip(),
            "answer": answer.strip(),
            "source": source,
            "recorded_at": _timestamp(now),
        }
    )
    _save(repo_root, profile_id, session)
    return session


def record_role_assessment(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    question_id: str,
    scores: Mapping[str, int],
    *,
    evidence: str,
    source: str,
    confidence: str,
    fatal_issues: Iterable[str] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if source not in ASSESSOR_SOURCES or confidence not in CONFIDENCE_LEVELS:
        raise RoleInterviewError("assessment source or confidence is invalid")
    question = next(
        (value for value in session["questions"] if value["question_id"] == question_id),
        None,
    )
    if question is None or not _has_response(session, question):
        raise RoleInterviewError("assessment requires completed question evidence")
    expected = set(question["rubric"]["dimensions"])
    if set(scores) != expected or any(type(value) is not int or value < 1 or value > 5 for value in scores.values()):
        raise RoleInterviewError("assessment must score every rubric dimension from 1 to 5")
    if not evidence.strip() or len(evidence) > 8000:
        raise RoleInterviewError("assessment evidence must contain 1 to 8000 characters")
    declared_fatal = tuple(dict.fromkeys(fatal_issues))
    unknown = set(declared_fatal) - set(question["rubric"]["fatal_issues"])
    if unknown:
        raise RoleInterviewError("assessment contains an unknown fatal issue")
    session["assessments"][question_id] = {
        "scores": dict(scores),
        "evidence": evidence.strip(),
        "source": source,
        "confidence": confidence,
        "fatal_issues": list(declared_fatal),
        "recorded_at": _timestamp(now),
    }
    _save(repo_root, profile_id, session)
    return session


def _question_score(question: Mapping[str, Any], assessment: Mapping[str, Any]) -> float:
    weighted = sum(
        float(dimension["weight"]) * int(assessment["scores"][name])
        for name, dimension in question["rubric"]["dimensions"].items()
    )
    score = (weighted - 1.0) / 4.0 * 100.0
    if assessment["fatal_issues"]:
        score = min(score, 40.0)
    return round(max(0.0, min(100.0, score)), 1)


def finish_role_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    summary: str = "",
    confirm_incomplete: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "active":
        raise RoleInterviewError("only an active role interview can be finished")
    unanswered = [
        q["question_id"] for q in session["questions"] if not _has_response(session, q)
    ]
    unscored = [q["question_id"] for q in session["questions"] if q["question_id"] not in session["assessments"]]
    expired = _remaining_seconds(session, now) == 0
    if (unanswered or unscored) and not (confirm_incomplete or expired):
        raise RoleInterviewError("interview evidence is incomplete; use explicit incomplete confirmation")

    question_scores: dict[str, float] = {}
    skill_values: dict[str, list[tuple[float, str]]] = {}
    weighted_total = 0.0
    completed_weight = 0.0
    for question in session["questions"]:
        question_id = question["question_id"]
        assessment = session["assessments"].get(question_id)
        if assessment is None:
            continue
        score = _question_score(question, assessment)
        question_scores[question_id] = score
        weight = float(question["round_weight"])
        weighted_total += score * weight
        completed_weight += weight
        for skill_id in question["skills"]:
            skill_values.setdefault(skill_id, []).append((score, question_id))
    completed = not unanswered and not unscored
    # Missing rounds contribute zero; partial evidence is never re-normalized.
    overall = round(weighted_total, 1)
    skill_scores = {
        skill_id: {
            "score": round(sum(value for value, _ in values) / len(values), 1),
            "evidence": [question_id for _, question_id in values],
        }
        for skill_id, values in sorted(skill_values.items())
    }
    weakest = sorted(skill_scores, key=lambda key: (skill_scores[key]["score"], key))[:3]
    result = {
        "completion_status": "completed" if completed else "incomplete",
        "overall_score": overall,
        "question_scores": question_scores,
        "skill_scores": skill_scores,
        "unanswered": unanswered,
        "unscored": unscored,
        "critical_gaps": weakest,
        "summary": summary.strip(),
        "finished_at": _timestamp(now),
        "expired": expired,
    }
    session["result"] = result
    session["status"] = "completed" if completed else "incomplete"
    session["timeline"].append(
        {"event": "finished", "timestamp": result["finished_at"]}
    )
    _save(repo_root, profile_id, session)
    _write_role_report(repo_root, profile_id, session)
    return session


def _write_role_report(repo_root: Path, profile_id: str, session: Mapping[str, Any]) -> None:
    root = _session_root(repo_root, profile_id, session["interview_id"])
    result = session["result"]
    lines = [
        f"# {session['interview_id']} — {session['role_id']}",
        "",
        f"- Status: **{result['completion_status']}**",
        f"- Seniority: `{session['seniority']}`",
        f"- Difficulty: `{session['difficulty']}`",
        f"- Overall score: **{result['overall_score']:.1f}/100**",
        "- Practice mastery: **unchanged**",
        "",
        "## Evidence-backed question scores",
        "",
    ]
    for question in session["questions"]:
        question_id = question["question_id"]
        score = result["question_scores"].get(question_id)
        lines.append(
            f"- {question_id} {question['title']}: "
            + (f"{score:.1f}" if score is not None else "unscored")
        )
    lines.extend(["", "## Skill scorecard", ""])
    for skill_id, value in result["skill_scores"].items():
        lines.append(
            f"- `{skill_id}`: {value['score']:.1f} — evidence {', '.join(value['evidence'])}"
        )
    if result["critical_gaps"]:
        lines.extend(["", "## Critical gaps", ""])
        lines.extend(f"- `{skill_id}`" for skill_id in result["critical_gaps"])
    if result["summary"]:
        lines.extend(["", "## Overall summary", "", result["summary"]])
    lines.extend(
        [
            "",
            "> This local mock-interview score is evidence for reflection; it is not an offer probability or Practice mastery evidence.",
            "",
        ]
    )
    _atomic_write(root / "report.md", "\n".join(lines).encode("utf-8"))
    _atomic_write(
        root / "report.json",
        (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )


def role_interview_report(
    repo_root: Path, profile_id: str, interview_id: str, *, format_name: str = "markdown"
) -> str:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["result"] is None:
        raise RoleInterviewError("role interview has no final report")
    root = _session_root(repo_root, profile_id, interview_id)
    if format_name == "json":
        return (root / "report.json").read_text(encoding="utf-8")
    if format_name != "markdown":
        raise RoleInterviewError("report format must be markdown or json")
    return (root / "report.md").read_text(encoding="utf-8")
