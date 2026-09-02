"""Deterministic, profile-local interviews driven by public role blueprints.

The engine freezes public questions and scoring contracts, while answers and
reports remain inside one ignored Profile.  It deliberately does not call an
LLM: a human interviewer or an optional AI client may deliver follow-ups and
record rubric evidence through this API.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
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
from .roles import InterviewItem, RoleCatalog, RoleCatalogError
from .submissions import SubmissionError, inspect_submission
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
# ``grader`` is an objective, deterministic source for coding-round evidence.
# It is intentionally distinct from human/AI/self judgement so reports and
# the desktop UI cannot mislabel a public-test result as a subjective score.
ASSESSOR_SOURCES = frozenset({"human", "ai", "self", "grader"})
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
    value = {
        "role_id": session["role_id"],
        "seniority": session["seniority"],
        "difficulty": session["difficulty"],
        "blueprint_id": session["blueprint_id"],
        "duration_minutes": session["duration_minutes"],
        "ai_mode": session["ai_mode"],
        "material_refs": session["material_refs"],
        "questions": session["questions"],
    }
    # Alpha.3 fallback sessions freeze their reduced delivery contract too.
    # Preserve the exact legacy payload for existing/full sessions so their
    # already-persisted fingerprints remain valid without a migration.
    for key in (
        "delivery_mode",
        "blueprint_coverage",
        "plan_mode",
        "plan_context_sha256",
    ):
        if key in session:
            value[key] = session[key]
    return value


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


def _effective_problem_skills(
    problem: Problem, role_catalog: RoleCatalog
) -> frozenset[str]:
    """Resolve coding skills from the ontology's single reverse index."""

    return frozenset(
        skill.id
        for skill in role_catalog.skills.values()
        if problem.id in skill.related_problems
    )


def _requires_torch(problem: Problem) -> bool:
    interface = problem.raw.get("interface", {})
    return isinstance(interface, Mapping) and str(interface.get("framework", "")).lower() == "pytorch"


def _coding_candidates(
    catalog: Catalog,
    role_catalog: RoleCatalog,
    track_ids: tuple[str, ...],
    difficulty: str,
    required_skills: tuple[str, ...],
    *,
    torch_available: bool,
) -> tuple[tuple[Problem, tuple[str, ...]], ...]:
    band = DIFFICULTY_BANDS[difficulty]
    tracks = set(track_ids)
    wanted = set(required_skills)
    candidates: list[tuple[Problem, tuple[str, ...]]] = []
    for problem in catalog.problems.values():
        effective_skills = _effective_problem_skills(problem, role_catalog)
        matched_skills = tuple(sorted(wanted.intersection(effective_skills)))
        if (
            problem.recommendable
            and not problem.id.startswith("CAP-")
            and tracks.intersection(problem.raw["tracks"])
            and problem.raw["difficulty"]["coding"] in band
            and matched_skills
            and (torch_available or not _requires_torch(problem))
        ):
            candidates.append((problem, matched_skills))
    return tuple(
        sorted(candidates, key=lambda candidate: candidate[0].id)
    )


def _item_candidates(
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    round_type: str,
    difficulty: str,
    required_skills: tuple[str, ...],
) -> tuple[tuple[InterviewItem, tuple[str, ...]], ...]:
    band = DIFFICULTY_BANDS[difficulty]
    wanted = set(required_skills)
    candidates: list[tuple[InterviewItem, tuple[str, ...]]] = []
    for item in role_catalog.items.values():
        matched_skills = tuple(sorted(wanted.intersection(item.skills)))
        if (
            item.status == "ready"
            and role_id in item.roles
            and seniority in item.seniority
            and item.kind == round_type
            and item.difficulty in band
            and matched_skills
        ):
            candidates.append((item, matched_skills))
    return tuple(sorted(candidates, key=lambda candidate: candidate[0].id))


def interview_preflight(
    repo_root: Path,
    catalog: Catalog,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    torch_available: bool | None = None,
) -> dict[str, Any]:
    """Return deterministic availability without writing a Profile or session."""

    if difficulty not in DIFFICULTY_BANDS:
        return {
            "available": False,
            "user_message": "面试难度无效，请选择 easy、medium 或 hard。",
            "missing_rounds": [],
            "missing_environment": [],
            "error_code": "DIFFICULTY_INVALID",
            "non_coding_fallback": {
                "available": False,
                "delivery_mode": "non_coding_fallback",
                "reason": "invalid_configuration",
            },
        }
    try:
        role = role_catalog.resolve_role(role_id)
        blueprint = role_catalog.blueprint_for(role.id, seniority)
    except RoleCatalogError:
        return {
            "available": False,
            "user_message": "当前岗位或求职阶段没有可用的固定面试蓝图。",
            "missing_rounds": [],
            "missing_environment": [],
            "error_code": "BLUEPRINT_UNAVAILABLE",
            "non_coding_fallback": {
                "available": False,
                "delivery_mode": "non_coding_fallback",
                "reason": "invalid_configuration",
            },
        }

    has_torch = (
        importlib.util.find_spec("torch") is not None
        if torch_available is None
        else bool(torch_available)
    )
    missing_rounds: list[dict[str, Any]] = []
    missing_environment: set[str] = set()
    round_views: list[dict[str, Any]] = []
    for round_index, round_value in enumerate(blueprint.rounds):
        missing_for_environment = False
        if round_value.type == "coding":
            candidates = _coding_candidates(
                catalog,
                role_catalog,
                role.required_tracks,
                difficulty,
                round_value.skills,
                torch_available=has_torch,
            )
            if not has_torch:
                with_torch = _coding_candidates(
                    catalog,
                    role_catalog,
                    role.required_tracks,
                    difficulty,
                    round_value.skills,
                    torch_available=True,
                )
                missing_for_environment = (
                    len(candidates) < round_value.item_count
                    and len(with_torch) >= round_value.item_count
                )
                if missing_for_environment:
                    missing_environment.add("pytorch")
            candidate_ids = [problem.id for problem, _ in candidates]
        else:
            candidates = _item_candidates(
                role_catalog,
                role_id=role.id,
                seniority=seniority,
                round_type=round_value.type,
                difficulty=difficulty,
                required_skills=round_value.skills,
            )
            candidate_ids = [item.id for item, _ in candidates]
        round_view = {
            "round_index": round_index,
            "type": round_value.type,
            "required_items": round_value.item_count,
            "candidate_ids": candidate_ids,
            "skills": list(round_value.skills),
            "duration_minutes": round_value.duration,
            "weight": round_value.weight,
        }
        round_views.append(round_view)
        if len(candidate_ids) < round_value.item_count:
            missing_rounds.append(
                {
                    **round_view,
                    "available_items": len(candidate_ids),
                    "reason": (
                        "missing_environment"
                        if missing_for_environment
                        else "no_strict_candidate"
                    ),
                }
            )
    available = not missing_rounds
    missing_only_for_environment = bool(missing_rounds) and all(
        value["reason"] == "missing_environment" for value in missing_rounds
    )
    coding_rounds = [value for value in round_views if value["type"] == "coding"]
    environment_blocked_rounds = {
        int(value["round_index"])
        for value in missing_rounds
        if value["reason"] == "missing_environment"
    }
    all_coding_rounds_blocked = bool(coding_rounds) and all(
        int(value["round_index"]) in environment_blocked_rounds
        for value in coding_rounds
    )
    included_rounds = [
        value
        for value in round_views
        if value["type"] != "coding"
        and len(value["candidate_ids"]) >= value["required_items"]
    ]
    fallback_available = (
        not available
        and missing_only_for_environment
        and all_coding_rounds_blocked
        and bool(included_rounds)
        and len(included_rounds)
        == sum(value["type"] != "coding" for value in round_views)
    )
    if fallback_available:
        omitted_rounds = [
            {
                "round_index": value["round_index"],
                "type": value["type"],
                "reason": value["reason"],
                "environment": "pytorch",
                "duration_minutes": value["duration_minutes"],
                "weight": value["weight"],
            }
            for value in missing_rounds
        ]
        fallback: dict[str, Any] = {
            "available": True,
            "delivery_mode": "non_coding_fallback",
            "full_blueprint": False,
            "duration_minutes": sum(
                int(value["duration_minutes"]) for value in included_rounds
            ),
            "coverage_weight": round(
                sum(float(value["weight"]) for value in included_rounds), 8
            ),
            "included_rounds": included_rounds,
            "omitted_rounds": omitted_rounds,
        }
    else:
        fallback = {
            "available": False,
            "delivery_mode": "non_coding_fallback",
            "reason": (
                "full_blueprint_available"
                if available
                else "non_environment_content_gap"
                if missing_rounds and not missing_only_for_environment
                else "mixed_coding_availability"
                if missing_only_for_environment and not all_coding_rounds_blocked
                else "no_non_coding_rounds"
            ),
        }
    return {
        "available": available,
        "role_id": role.id,
        "seniority": seniority,
        "difficulty": difficulty,
        "blueprint_id": blueprint.id,
        "user_message": (
            "当前配置可用。"
            if available
            else "完整岗位蓝图需要 PyTorch 代码环节；当前环境可选择明确标记的非代码专项面试。"
            if fallback_available
            else "当前配置缺少满足岗位、难度与技能要求的固定面试题。"
        ),
        "missing_rounds": missing_rounds,
        "missing_environment": sorted(missing_environment),
        "rounds": round_views,
        "error_code": (
            ""
            if available
            else "PYTORCH_REQUIRED"
            if fallback_available
            else "INTERVIEW_UNAVAILABLE"
        ),
        "non_coding_fallback": fallback,
    }


def _item_question(
    item: InterviewItem,
    *,
    question_id: str,
    round_index: int,
    round_weight: float,
    timebox_minutes: int,
    skills: tuple[str, ...],
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
        "skills": list(skills),
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
        "skills": list(skills),
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


def _generated_non_coding_question(
    generated_value: Mapping[str, Any],
    *,
    question_id: str,
    round_index: int,
    round_type: str,
    round_weight: float,
    timebox_minutes: int,
    skills: tuple[str, ...],
    plan_context_sha256: str,
) -> dict[str, Any]:
    """Freeze one provider/process turn against local skills and rubric facts."""

    if generated_value.get("kind") != round_type:
        raise RoleInterviewError(
            "generated interview question kind does not match blueprint"
        )
    title = generated_value.get("title")
    prompt = generated_value.get("prompt")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise RoleInterviewError("generated question title is invalid")
    if not isinstance(prompt, str) or not 10 <= len(prompt.strip()) <= 5000:
        raise RoleInterviewError("generated question prompt is invalid")
    source_kind = str(generated_value.get("source_kind") or "ai_generated")
    if source_kind not in {"ai_generated", "process_opening"}:
        raise RoleInterviewError("generated question source kind is invalid")
    rubric = {
        "dimensions": {
            "skill_depth": {
                "weight": 0.6,
                "anchors": {
                    "1": "核心概念或适用边界存在明显错误，无法回应题目约束。",
                    "3": "核心判断基本正确，但实现、权衡或边界证据仍不完整。",
                    "5": "能够准确应用目标技能，并清楚解释约束、权衡和失败边界。",
                },
            },
            "evidence_and_reasoning": {
                "weight": 0.4,
                "anchors": {
                    "1": "只有结论或术语，缺少可核对的推理与证据。",
                    "3": "给出部分推理或实例，但假设、不确定性或取舍未说清。",
                    "5": "事实、推断和不确定性区分清楚，证据与结论可相互对应。",
                },
            },
        },
        "fatal_issues": [
            "fabricates_candidate_evidence",
            "ignores_question_constraints",
        ],
    }
    rubric_sha256 = hashlib.sha256(
        json.dumps(
            rubric, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    source_id = f"blueprint-round-{round_index + 1}-{round_type}"
    source_payload = {
        "title": title.strip(),
        "prompt": prompt.strip(),
        "context_sha256": plan_context_sha256,
        "rubric_id": source_id,
        "rubric_sha256": rubric_sha256,
        "skills": list(skills),
    }
    return {
        "question_id": question_id,
        "round_index": round_index,
        "kind": round_type,
        "title": title.strip(),
        "timebox_minutes": timebox_minutes,
        "round_weight": round_weight,
        "skills": list(skills),
        "source": {
            "kind": source_kind,
            "id": source_id,
            "sha256": hashlib.sha256(
                json.dumps(
                    source_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "context_sha256": plan_context_sha256,
            "rubric_sha256": rubric_sha256,
        },
        "prompt": prompt.strip(),
        "rubric": rubric,
    }


def _personalized_round_selection(
    catalog: Catalog,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    torch_available: bool,
) -> dict[str, Any]:
    """Allow Blueprint/skills AI rounds; keep coding locally validated only."""

    if difficulty not in DIFFICULTY_BANDS:
        raise RoleInterviewError("difficulty must be easy, medium, or hard")
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)
    included: list[int] = []
    omitted: list[dict[str, Any]] = []
    for round_index, round_value in enumerate(blueprint.rounds):
        if round_value.type != "coding":
            included.append(round_index)
            continue
        candidates = _coding_candidates(
            catalog,
            role_catalog,
            role.required_tracks,
            difficulty,
            round_value.skills,
            torch_available=torch_available,
        )
        if len(candidates) >= round_value.item_count:
            included.append(round_index)
            continue
        with_torch = _coding_candidates(
            catalog,
            role_catalog,
            role.required_tracks,
            difficulty,
            round_value.skills,
            torch_available=True,
        )
        missing_environment = (
            not torch_available and len(with_torch) >= round_value.item_count
        )
        omitted.append(
            {
                "round_index": round_index,
                "type": "coding",
                "reason": (
                    "missing_environment"
                    if missing_environment
                    else "no_validated_local_coding"
                ),
                "environment": "pytorch" if missing_environment else "catalog",
                "duration_minutes": round_value.duration,
                "weight": round_value.weight,
            }
        )
    if not included:
        raise RoleInterviewError("当前岗位蓝图没有可生成的面试轮次")
    if omitted:
        return {
            "delivery_mode": "non_coding_fallback",
            "included_round_indices": set(included),
            "duration_minutes": sum(
                blueprint.rounds[index].duration for index in included
            ),
            "blueprint_coverage": {
                "full_blueprint": False,
                "coverage_weight": round(
                    sum(blueprint.rounds[index].weight for index in included), 8
                ),
                "included_round_indices": included,
                "omitted_rounds": omitted,
            },
        }
    return {
        "delivery_mode": "full_blueprint",
        "included_round_indices": None,
        "duration_minutes": blueprint.duration_minutes,
        "blueprint_coverage": None,
    }


def _build_questions(
    repo_root: Path,
    catalog: Catalog,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    seed: int,
    included_round_indices: set[int] | None,
    torch_available: bool,
    generated_questions: Iterable[Mapping[str, Any]] | None = None,
    plan_context_sha256: str | None = None,
) -> list[dict[str, Any]]:
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)
    generated = tuple(generated_questions or ())
    if plan_context_sha256 is not None and not generated:
        raise RoleInterviewError("AI interview plan must contain generated questions")
    generated_by_position: dict[tuple[int, int], Mapping[str, Any]] = {}
    for value in generated:
        if not isinstance(value, Mapping):
            raise RoleInterviewError("generated interview questions must be objects")
        try:
            raw_round_index = value["round_index"]
            raw_item_index = value["item_index"]
        except KeyError as error:
            raise RoleInterviewError("generated interview question position is invalid") from error
        # The position is part of the frozen plan identity.  Do not coerce
        # strings, floats, or bools here: ``bool`` is an ``int`` subclass and
        # accepting it would let malformed provider data address another
        # question silently.
        if type(raw_round_index) is not int or type(raw_item_index) is not int:
            raise RoleInterviewError("generated interview question position is invalid")
        position = (raw_round_index, raw_item_index)
        if position in generated_by_position:
            raise RoleInterviewError("generated interview question positions must be unique")
        generated_by_position[position] = value
    if generated:
        if (
            not isinstance(plan_context_sha256, str)
            or len(plan_context_sha256) != 64
            or any(character not in "0123456789abcdef" for character in plan_context_sha256)
        ):
            raise RoleInterviewError("AI interview plan needs a valid context SHA-256")

    questions: list[dict[str, Any]] = []
    used_generated: set[tuple[int, int]] = set()
    used_items: set[str] = set()
    used_problems: set[str] = set()
    number = 1
    for round_index, round_value in enumerate(blueprint.rounds):
        if included_round_indices is not None and round_index not in included_round_indices:
            continue
        each_timebox = max(1, round_value.duration // round_value.item_count)
        for item_index in range(round_value.item_count):
            question_id = f"q-{number:03d}"
            identity = (
                f"role-interview-v1|{role.id}|{seniority}|{difficulty}|{seed}|"
                f"{round_index}|{item_index}"
            )
            if round_value.type == "coding":
                coding_pool = _coding_candidates(
                    catalog,
                    role_catalog,
                    role.required_tracks,
                    difficulty,
                    round_value.skills,
                    torch_available=torch_available,
                )
                available = tuple(
                    candidate
                    for candidate in coding_pool
                    if candidate[0].id not in used_problems
                )
                problem, matched_skills = _stable_choice(available, identity)
                used_problems.add(problem.id)
                question = _coding_question(
                    repo_root,
                    problem,
                    question_id=question_id,
                    round_index=round_index,
                    round_weight=round_value.weight,
                    timebox_minutes=each_timebox,
                    skills=matched_skills,
                )
            else:
                position = (round_index, item_index)
                generated_value = generated_by_position.get(position)
                if generated_value is not None:
                    assert plan_context_sha256 is not None
                    question = _generated_non_coding_question(
                        generated_value,
                        question_id=question_id,
                        round_index=round_index,
                        round_type=round_value.type,
                        round_weight=round_value.weight,
                        timebox_minutes=each_timebox,
                        skills=round_value.skills,
                        plan_context_sha256=plan_context_sha256,
                    )
                    used_generated.add(position)
                else:
                    pool = tuple(
                        candidate
                        for candidate in _item_candidates(
                            role_catalog,
                            role_id=role.id,
                            seniority=seniority,
                            round_type=round_value.type,
                            difficulty=difficulty,
                            required_skills=round_value.skills,
                        )
                        if candidate[0].id not in used_items
                    )
                    item, matched_skills = _stable_choice(pool, identity)
                    used_items.add(item.id)
                    question = _item_question(
                        item,
                        question_id=question_id,
                        round_index=round_index,
                        round_weight=round_value.weight,
                        timebox_minutes=each_timebox,
                        skills=matched_skills,
                    )
            questions.append(question)
            number += 1
    if generated and used_generated != set(generated_by_position):
        raise RoleInterviewError(
            "generated interview questions do not exactly cover the non-coding blueprint"
        )
    expected_generated = sum(
        round_value.item_count
        for round_index, round_value in enumerate(blueprint.rounds)
        if round_value.type != "coding"
        and (included_round_indices is None or round_index in included_round_indices)
    )
    if generated and len(used_generated) != expected_generated:
        raise RoleInterviewError(
            "generated interview plan is missing a non-coding blueprint question"
        )
    return questions


def _create_session_from_plan(
    repo_root: Path,
    profile_id: str,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    blueprint_id: str,
    duration_minutes: int,
    ai_mode: str,
    material_refs: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    delivery_mode: str,
    blueprint_coverage: Mapping[str, Any] | None,
    plan_context_sha256: str | None,
    now: datetime | None,
) -> dict[str, Any]:
    paths = profile_paths(repo_root, profile_id)
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
        "role_id": role_id,
        "seniority": seniority,
        "difficulty": difficulty,
        "blueprint_id": blueprint_id,
        "duration_minutes": duration_minutes,
        "ai_mode": ai_mode,
        "material_refs": material_refs,
        "questions": questions,
        "plan_fingerprint": "0" * 64,
        "started_at": None,
        "deadline": None,
        "paused_at": None,
        "paused_remaining_seconds": None,
        "answers": {},
        "coding_evidence": {},
        "assessments": {},
        "followups": [],
        "timeline": [{"event": "created", "timestamp": created_at}],
        "result": None,
    }
    if delivery_mode == "non_coding_fallback" and blueprint_coverage is not None:
        session["delivery_mode"] = delivery_mode
        session["blueprint_coverage"] = dict(blueprint_coverage)
    elif delivery_mode == "dynamic_ai":
        # Dynamic sessions persist only turns that have actually been asked.
        # Future questions remain provider state, not hidden session content.
        session["delivery_mode"] = delivery_mode
    if plan_context_sha256 is not None:
        # A dynamic session records only the turns already asked.  Keep its
        # mode explicit so readers never mistake it for a pre-generated plan.
        session["plan_mode"] = (
            "dynamic_ai" if delivery_mode == "dynamic_ai" else "ai_generated"
        )
        session["plan_context_sha256"] = plan_context_sha256
    try:
        _write_session(repo_root, root / "session.json", session)
    except Exception:
        for child in (root / "answers", root / "coding"):
            child.rmdir()
        root.rmdir()
        raise
    return session


def create_dynamic_role_interview(
    repo_root: Path,
    profile_id: str,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    ai_mode: str,
    initial_question: Mapping[str, Any],
    plan_context_sha256: str,
    material_refs: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a dynamic interview containing only its first real question.

    The provider chooses one non-coding question at a time.  Role skills,
    process, timing and coding eligibility remain local facts; future turns
    are deliberately not materialized here.
    """

    if ai_mode not in {"provider", "codex"}:
        raise RoleInterviewError("dynamic interviews require provider or codex AI")
    if not isinstance(plan_context_sha256, str) or len(plan_context_sha256) != 64:
        raise RoleInterviewError("dynamic interview needs a valid context SHA-256")
    if any(character not in "0123456789abcdef" for character in plan_context_sha256):
        raise RoleInterviewError("dynamic interview needs a valid context SHA-256")
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)
    non_coding = [
        (index, round_value)
        for index, round_value in enumerate(blueprint.rounds)
        if round_value.type != "coding"
    ]
    if not non_coding:
        raise RoleInterviewError("this role has no non-coding interview round")
    round_index, round_value = non_coding[0]
    if not isinstance(initial_question, Mapping):
        raise RoleInterviewError("initial interview question must be an object")
    if initial_question.get("kind") != round_value.type:
        raise RoleInterviewError("initial question kind does not match the first round")
    question = _generated_non_coding_question(
        initial_question,
        question_id="q-001",
        round_index=round_index,
        round_type=round_value.type,
        round_weight=round_value.weight,
        timebox_minutes=max(1, round_value.duration),
        skills=round_value.skills,
        plan_context_sha256=plan_context_sha256,
    )
    if not material_refs:
        material_refs = []
    return _create_session_from_plan(
        repo_root,
        profile_id,
        role_id=role.id,
        seniority=seniority,
        difficulty=difficulty,
        blueprint_id=blueprint.id,
        duration_minutes=blueprint.duration_minutes,
        ai_mode=ai_mode,
        material_refs=list(material_refs),
        questions=[question],
        delivery_mode="dynamic_ai",
        blueprint_coverage=None,
        plan_context_sha256=plan_context_sha256,
        now=now,
    )


def append_dynamic_role_question(
    repo_root: Path,
    profile_id: str,
    role_catalog: RoleCatalog,
    interview_id: str,
    *,
    question: Mapping[str, Any],
    plan_context_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append exactly one provider question after the current turn completes."""

    session = load_role_interview(repo_root, profile_id, interview_id)
    if session.get("delivery_mode") != "dynamic_ai":
        raise RoleInterviewError("only dynamic AI interviews accept generated turns")
    if session.get("status") != "active":
        raise RoleInterviewError("dynamic question requires an active interview")
    if not isinstance(question, Mapping):
        raise RoleInterviewError("generated interview question must be an object")
    if any(not _is_complete(session, value) for value in session["questions"]):
        raise RoleInterviewError("complete the current interview turn before asking another")
    if session.get("plan_context_sha256") != plan_context_sha256:
        raise RoleInterviewError("dynamic interview context is stale; start a new turn")
    role = role_catalog.resolve_role(session["role_id"])
    blueprint = role_catalog.blueprint_for(role.id, session["seniority"])
    requested_kind = question.get("kind")
    matching = [
        (index, round_value)
        for index, round_value in enumerate(blueprint.rounds)
        if round_value.type != "coding" and round_value.type == requested_kind
    ]
    if not matching:
        raise RoleInterviewError("generated question kind is not allowed by this role")
    round_index, round_value = matching[0]
    if len(session["questions"]) >= 20:
        raise RoleInterviewError("dynamic interview reached its 20-question limit")
    question_id = f"q-{len(session['questions']) + 1:03d}"
    appended = _generated_non_coding_question(
        question,
        question_id=question_id,
        round_index=round_index,
        round_type=round_value.type,
        round_weight=round_value.weight,
        timebox_minutes=max(1, round_value.duration),
        skills=round_value.skills,
        plan_context_sha256=plan_context_sha256,
    )
    session["questions"].append(appended)
    session["timeline"].append(
        {
            "event": "question_generated",
            "question_id": question_id,
            "timestamp": _timestamp(now),
        }
    )
    _save(repo_root, profile_id, session)
    return session


def _material_references(
    repo_root: Path,
    profile_id: str,
    material_ids: Iterable[str],
    *,
    consent_materials: bool,
) -> list[dict[str, Any]]:
    selected = tuple(dict.fromkeys(material_ids))
    if selected and not consent_materials:
        raise RoleInterviewError("materials require explicit per-interview consent")
    references: list[dict[str, Any]] = []
    for material_id in selected:
        try:
            material = get_material(repo_root, profile_id, material_id)
        except MaterialError as error:
            raise RoleInterviewError(str(error)) from error
        if not material.ai_access:
            raise RoleInterviewError(f"material does not allow AI access: {material.id}")
        references.append(
            {
                "id": material.id,
                "sha256": material.sha256,
                "kind": material.kind,
                "title": material.title,
                "allowed_use": "role_interview",
            }
        )
    return references


def preview_personalized_role_interview(
    repo_root: Path,
    profile_id: str,
    catalog: Catalog,
    role_catalog: RoleCatalog,
    *,
    role_id: str,
    seniority: str,
    difficulty: str,
    generated_questions: Iterable[Mapping[str, Any]],
    plan_context_sha256: str,
    material_ids: Iterable[str] = (),
    consent_materials: bool = False,
    seed: int = 0,
) -> dict[str, Any]:
    """Return a no-write preview for the first real personalized AI path."""

    repo_root = repo_root.resolve()
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    ensure_profile_is_ignored(repo_root, profile_id)
    if type(seed) is not int or isinstance(seed, bool) or seed < 0:
        raise RoleInterviewError("seed must be a non-negative integer")
    torch_available = importlib.util.find_spec("torch") is not None
    selection = _personalized_round_selection(
        catalog,
        role_catalog,
        role_id=role_id,
        seniority=seniority,
        difficulty=difficulty,
        torch_available=torch_available,
    )
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)
    material_refs = _material_references(
        repo_root,
        profile_id,
        material_ids,
        consent_materials=consent_materials,
    )
    questions = _build_questions(
        repo_root,
        catalog,
        role_catalog,
        role_id=role.id,
        seniority=seniority,
        difficulty=difficulty,
        seed=seed,
        included_round_indices=selection["included_round_indices"],
        torch_available=torch_available,
        generated_questions=generated_questions,
        plan_context_sha256=plan_context_sha256,
    )
    value = {
        "plan_mode": "ai_generated",
        "role_id": role.id,
        "role_title": role.title,
        "seniority": seniority,
        "difficulty": difficulty,
        "blueprint_id": blueprint.id,
        "duration_minutes": selection["duration_minutes"],
        "delivery_mode": selection["delivery_mode"],
        "material_refs": material_refs,
        "questions": questions,
        "plan_context_sha256": plan_context_sha256,
    }
    if selection["blueprint_coverage"] is not None:
        value["blueprint_coverage"] = selection["blueprint_coverage"]
    value["draft_fingerprint"] = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return value


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
    delivery_mode: str = "full_blueprint",
    generated_questions: Iterable[Mapping[str, Any]] | None = None,
    plan_context_sha256: str | None = None,
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
    if delivery_mode not in {"full_blueprint", "non_coding_fallback"}:
        raise RoleInterviewError(
            "delivery mode must be full_blueprint or non_coding_fallback"
        )
    if type(seed) is not int or isinstance(seed, bool) or seed < 0:
        raise RoleInterviewError("seed must be a non-negative integer")
    if generated_questions is not None and ai_mode == "disabled":
        raise RoleInterviewError("AI-generated plans require an enabled AI mode")
    role = role_catalog.resolve_role(role_id)
    blueprint = role_catalog.blueprint_for(role.id, seniority)
    torch_available = importlib.util.find_spec("torch") is not None
    selection: Mapping[str, Any] | None = None
    if generated_questions is not None:
        generated_questions = tuple(generated_questions)
        selection = _personalized_round_selection(
            catalog,
            role_catalog,
            role_id=role.id,
            seniority=seniority,
            difficulty=difficulty,
            torch_available=torch_available,
        )
        delivery_mode = str(selection["delivery_mode"])
        included_round_indices = selection["included_round_indices"]
    else:
        availability = interview_preflight(
            repo_root,
            catalog,
            role_catalog,
            role_id=role.id,
            seniority=seniority,
            difficulty=difficulty,
            torch_available=torch_available,
        )
    if generated_questions is None and delivery_mode == "full_blueprint":
        if not availability["available"]:
            raise RoleInterviewError(availability["user_message"])
        included_round_indices = None
    elif generated_questions is None:
        fallback = availability["non_coding_fallback"]
        if not fallback["available"]:
            raise RoleInterviewError(
                "non-coding fallback is unavailable for this role interview configuration"
            )
        included_round_indices = {
            int(value["round_index"]) for value in fallback["included_rounds"]
        }

    material_refs = _material_references(
        repo_root,
        profile_id,
        material_ids,
        consent_materials=consent_materials,
    )

    questions = _build_questions(
        repo_root,
        catalog,
        role_catalog,
        role_id=role.id,
        seniority=seniority,
        difficulty=difficulty,
        seed=seed,
        included_round_indices=included_round_indices,
        torch_available=torch_available,
        generated_questions=generated_questions,
        plan_context_sha256=plan_context_sha256,
    )
    blueprint_coverage: Mapping[str, Any] | None = (
        selection["blueprint_coverage"] if selection is not None else None
    )
    if generated_questions is None and delivery_mode == "non_coding_fallback":
        fallback = availability["non_coding_fallback"]
        blueprint_coverage = {
            "full_blueprint": False,
            "coverage_weight": fallback["coverage_weight"],
            "included_round_indices": [
                int(value["round_index"]) for value in fallback["included_rounds"]
            ],
            "omitted_rounds": fallback["omitted_rounds"],
        }
    return _create_session_from_plan(
        repo_root,
        profile_id,
        role_id=role.id,
        seniority=seniority,
        difficulty=difficulty,
        blueprint_id=blueprint.id,
        duration_minutes=(
            int(selection["duration_minutes"])
            if selection is not None
            else blueprint.duration_minutes
            if delivery_mode == "full_blueprint"
            else int(availability["non_coding_fallback"]["duration_minutes"])
        ),
        ai_mode=ai_mode,
        material_refs=material_refs,
        questions=questions,
        delivery_mode=delivery_mode,
        blueprint_coverage=blueprint_coverage,
        plan_context_sha256=(
            plan_context_sha256 if generated_questions is not None else None
        ),
        now=now,
    )


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


def list_role_interviews(
    repo_root: Path, profile_id: str
) -> tuple[dict[str, Any], ...]:
    """List only the explicitly selected Profile's role-interview sessions."""

    paths = profile_paths(repo_root, profile_id)
    root = ensure_profile_path_is_safe(
        repo_root, profile_id, paths.interviews_root
    )
    if not root.exists():
        return ()
    sessions: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        name = entry.name
        if not (
            name.startswith(ROLE_INTERVIEW_ID_PREFIX)
            and len(name)
            == len(ROLE_INTERVIEW_ID_PREFIX) + ROLE_INTERVIEW_ID_WIDTH
            and name[-ROLE_INTERVIEW_ID_WIDTH:].isdigit()
        ):
            continue
        sessions.append(load_role_interview(repo_root, profile_id, name))
    return tuple(sessions)


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
    session["paused_at"] = None
    session["paused_remaining_seconds"] = None
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


def _next_role_question(session: Mapping[str, Any]) -> dict[str, Any] | None:
    """Select the next frozen question without depending on clock state."""

    return next(
        (value for value in session["questions"] if not _is_complete(session, value)),
        None,
    )


def role_interview_state(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return the current frozen question for an active or paused session.

    This is a presentation/recovery view only. Mutation APIs continue to
    require ``active`` and therefore cannot answer, assess, or grade while
    the interview is paused.
    """

    session = load_role_interview(repo_root, profile_id, interview_id)
    status = session["status"]
    if status == "paused":
        remaining = session.get("paused_remaining_seconds")
        if type(remaining) is not int or remaining <= 0:
            raise RoleInterviewError("paused role interview has invalid remaining time")
    elif status == "active":
        remaining = _remaining_seconds(session, now)
        if remaining == 0:
            raise RoleInterviewError("role interview time has expired; finish it as incomplete")
    else:
        raise RoleInterviewError("role interview is not active or paused")
    return {
        "question": _next_role_question(session),
        "remaining_seconds": remaining,
        "status": status,
    }


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
    state = role_interview_state(
        repo_root, profile_id, interview_id, now=now
    )
    return {
        "question": state["question"],
        "remaining_seconds": state["remaining_seconds"],
    }


def pause_role_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "active":
        raise RoleInterviewError("only an active role interview can be paused")
    current = _parse_timestamp(_timestamp(now))
    remaining = _remaining_seconds(session, current)
    if remaining <= 0:
        raise RoleInterviewError("role interview time has expired; finish it as incomplete")
    paused_at = _timestamp(current)
    session["status"] = "paused"
    session["paused_at"] = paused_at
    session["paused_remaining_seconds"] = remaining
    session["deadline"] = None
    session["timeline"].append({"event": "paused", "timestamp": paused_at})
    _save(repo_root, profile_id, session)
    return session


def resume_role_interview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "paused":
        raise RoleInterviewError("only a paused role interview can be resumed")
    remaining = session.get("paused_remaining_seconds")
    if type(remaining) is not int or remaining <= 0:
        raise RoleInterviewError("paused role interview has invalid remaining time")
    current = _parse_timestamp(_timestamp(now))
    resumed_at = _timestamp(current)
    session["status"] = "active"
    session["deadline"] = _timestamp(current + timedelta(seconds=remaining))
    session["paused_at"] = None
    session["paused_remaining_seconds"] = None
    session["timeline"].append({"event": "resumed", "timestamp": resumed_at})
    _save(repo_root, profile_id, session)
    return session


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


def role_interview_answer_text(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    question_id: str,
) -> str:
    """Read one locked text answer only from its canonical Profile path."""

    session = load_role_interview(repo_root, profile_id, interview_id)
    record = session.get("answers", {}).get(question_id)
    if not isinstance(record, Mapping):
        raise RoleInterviewError("interview answer evidence is missing")
    try:
        path = ensure_profile_path_is_safe(
            repo_root,
            profile_id,
            _session_root(repo_root, profile_id, interview_id)
            / "answers"
            / f"{question_id}.md",
            must_exist=True,
        )
        expected_relative = path.relative_to(
            profile_paths(repo_root, profile_id).root
        ).as_posix()
        if record.get("relative_path") != expected_relative:
            raise RoleInterviewError("interview answer path is invalid")
        content = path.read_bytes()
        text = content.decode("utf-8").strip()
    except (OSError, UnicodeError, WorkspaceError) as error:
        raise RoleInterviewError("interview answer evidence is unavailable") from error
    if not text or record.get("sha256") != hashlib.sha256(content).hexdigest():
        raise RoleInterviewError("interview answer evidence failed integrity validation")
    return text


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
    if session["status"] != "active":
        raise RoleInterviewError("follow-up may only be recorded for an active interview")
    current = current_role_question(repo_root, profile_id, interview_id, now=now)["question"]
    if current is None or current["question_id"] != parent_question_id:
        raise RoleInterviewError("follow-up must belong to the current question")
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


def _validated_coding_assessment(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    question: Mapping[str, Any],
    assessment: Mapping[str, Any],
    session: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Validate objective coding evidence before it can affect a report.

    The persisted Grader record is keyed by question and by submission SHA.
    Re-checking the file here closes both common loopholes: a caller cannot
    submit a subjective score for a coding round, and editing the file after
    the Grader ran invalidates the score instead of silently reusing it.
    """

    if assessment.get("source") != "grader":
        raise RoleInterviewError(
            "coding assessment must use the local Grader evidence"
        )
    question_id = str(question.get("question_id") or "")
    coding_evidence = (session.get("coding_evidence") or {}).get(question_id)
    if not isinstance(coding_evidence, Mapping):
        raise RoleInterviewError("coding assessment requires a recorded Grader result")
    status = coding_evidence.get("status")
    # A timeout/import/collection/internal failure is diagnostic evidence, not
    # a candidate score.  Only a completed assertion run may be recorded.
    if status not in {"passed", "failed"}:
        raise RoleInterviewError(
            "coding assessment requires a completed passed/failed Grader result"
        )
    try:
        submission_root = (
            _session_root(repo_root, profile_id, interview_id)
            / "coding"
            / question_id
        )
        submission_path = ensure_profile_path_is_safe(
            repo_root,
            profile_id,
            submission_root / "submission.py",
            must_exist=True,
        )
        current_sha = inspect_submission(submission_path, submission_root).sha256
    except (OSError, WorkspaceError, SubmissionError) as error:
        raise RoleInterviewError(
            "coding submission is unavailable; rerun the local Grader"
        ) from error
    tested_sha = str(coding_evidence.get("submission_sha256") or "")
    if not tested_sha or tested_sha != current_sha:
        raise RoleInterviewError(
            "coding submission changed after Grader evidence; rerun the local Grader"
        )
    expected_score = 5 if status == "passed" else 1
    scores = assessment.get("scores")
    if not isinstance(scores, Mapping) or any(
        value != expected_score for value in scores.values()
    ):
        raise RoleInterviewError(
            "coding score must match the local Grader result (5=passed, 1=failed)"
        )
    return coding_evidence


def _validate_answer_assessment_evidence(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    question_id: str,
    assessment: Mapping[str, Any],
    session: Mapping[str, Any],
) -> None:
    """Re-check a locked text answer before reusing its assessment."""

    answer_record = (session.get("answers") or {}).get(question_id)
    if not isinstance(answer_record, Mapping):
        raise RoleInterviewError(
            "answer evidence is missing; the assessment cannot be reused"
        )
    try:
        role_interview_answer_text(repo_root, profile_id, interview_id, question_id)
    except RoleInterviewError as error:
        raise RoleInterviewError(
            "locked answer changed after assessment; the question is now unscored"
        ) from error
    recorded_sha = str(answer_record.get("sha256") or "")
    assessed_sha = str(assessment.get("answer_sha256") or "")
    if assessed_sha and assessed_sha != recorded_sha:
        raise RoleInterviewError(
            "assessment is bound to a different answer revision; the question is now unscored"
        )


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
    followup_ids: Iterable[str] = (),
) -> dict[str, Any]:
    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["status"] != "active":
        raise RoleInterviewError("assessment may only be recorded for an active interview")
    if question_id in session["assessments"]:
        raise RoleInterviewError("the current question already has recorded assessment evidence")
    if source not in ASSESSOR_SOURCES or confidence not in CONFIDENCE_LEVELS:
        raise RoleInterviewError("assessment source or confidence is invalid")
    question = next(
        (value for value in session["questions"] if value["question_id"] == question_id),
        None,
    )
    if question is None or not _has_response(session, question):
        raise RoleInterviewError("assessment requires completed question evidence")
    if source == "grader" and question["kind"] != "coding":
        raise RoleInterviewError(
            "grader evidence is only valid for coding interview questions"
        )
    if question["kind"] == "coding":
        # A coding round has one deterministic source of truth: the public
        # Grader result bound to the exact submission revision.  Accepting a
        # manually supplied ``human``/``ai`` score here would let a failed or
        # stale implementation become a fabricated high score.
        coding_evidence = _validated_coding_assessment(
            repo_root,
            profile_id,
            interview_id,
            question,
            {
                "source": source,
                "scores": scores,
            },
            session,
        )
        # Store a canonical, machine-bound evidence line.  Caller prose is
        # not allowed to masquerade as an objective test report.
        evidence = (
            "Local Grader objective evidence: "
            f"status={coding_evidence.get('status')}; "
            f"passed={coding_evidence.get('passed', 0)}; "
            f"failed={coding_evidence.get('failed', 0)}; "
            f"duration_ms={coding_evidence.get('duration_ms', 0)}; "
            f"submission_sha256={coding_evidence.get('submission_sha256')}"
        )
    answer_sha256 = ""
    if question["kind"] != "coding":
        role_interview_answer_text(
            repo_root, profile_id, interview_id, question_id
        )
        answer_record = (session.get("answers") or {}).get(question_id)
        if isinstance(answer_record, Mapping):
            answer_sha256 = str(answer_record.get("sha256") or "")
    current = current_role_question(repo_root, profile_id, interview_id, now=now)["question"]
    if current is None or current["question_id"] != question_id:
        raise RoleInterviewError("only the current question may be assessed")
    expected = set(question["rubric"]["dimensions"])
    if set(scores) != expected or any(type(value) is not int or value < 1 or value > 5 for value in scores.values()):
        raise RoleInterviewError("assessment must score every rubric dimension from 1 to 5")
    if not evidence.strip() or len(evidence) > 8000:
        raise RoleInterviewError("assessment evidence must contain 1 to 8000 characters")
    declared_fatal = tuple(dict.fromkeys(fatal_issues))
    unknown = set(declared_fatal) - set(question["rubric"]["fatal_issues"])
    if unknown:
        raise RoleInterviewError("assessment contains an unknown fatal issue")
    linked_followups = tuple(dict.fromkeys(followup_ids))
    followup_by_id = {}
    for item in session.get("followups", []):
        if not isinstance(item, Mapping):
            continue
        followup_id = item.get("followup_id")
        parent_question_id = item.get("parent_question_id")
        if followup_id and parent_question_id:
            followup_by_id[followup_id] = item
    if any(
        followup_id not in followup_by_id
        or followup_by_id[followup_id]["parent_question_id"] != question_id
        for followup_id in linked_followups
    ):
        raise RoleInterviewError("assessment follow-up link does not belong to this question")
    assessment = {
        "scores": dict(scores),
        "evidence": evidence.strip(),
        "source": source,
        "confidence": confidence,
        "fatal_issues": list(declared_fatal),
        "recorded_at": _timestamp(now),
    }
    # Keep the persisted shape of legacy assessments unchanged when there is
    # no follow-up.  The optional field is emitted only when it carries data.
    if linked_followups:
        assessment["followup_ids"] = list(linked_followups)
    if answer_sha256:
        assessment["answer_sha256"] = answer_sha256
    session["assessments"][question_id] = assessment
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
    paused = session["status"] == "paused"
    if session["status"] not in {"active", "paused"}:
        raise RoleInterviewError("only an active or paused role interview can be finished")
    if paused and not confirm_incomplete:
        raise RoleInterviewError("paused interview requires explicit incomplete confirmation")
    unanswered = [
        q["question_id"] for q in session["questions"] if not _has_response(session, q)
    ]
    unscored = [
        q["question_id"]
        for q in session["questions"]
        if _has_response(session, q) and q["question_id"] not in session["assessments"]
    ]
    expired = (not paused) and _remaining_seconds(session, now) == 0
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
        if question["kind"] == "coding":
            _validated_coding_assessment(
                repo_root,
                profile_id,
                interview_id,
                question,
                assessment,
                session,
            )
        else:
            _validate_answer_assessment_evidence(
                repo_root,
                profile_id,
                interview_id,
                question_id,
                assessment,
                session,
            )
        score = _question_score(question, assessment)
        question_scores[question_id] = score
        weight = float(question["round_weight"])
        weighted_total += score * weight
        completed_weight += weight
        for skill_id in question["skills"]:
            skill_values.setdefault(skill_id, []).append((score, question_id))
    evidence_complete = not paused and not unanswered and not unscored
    completed = (
        evidence_complete
        and session.get("delivery_mode", "full_blueprint") == "full_blueprint"
    )
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
    assessments = session.get("assessments", {})
    score_scope = (
        "unscored"
        if not assessments
        else "complete"
        if result["completion_status"] == "completed"
        else "partial"
    )
    if score_scope == "unscored":
        overall_line = "- Overall score: **unscored** (no assessment evidence)"
    elif score_scope == "complete":
        overall_line = f"- Overall score: **{result['overall_score']:.1f}/100**"
    else:
        overall_line = (
            f"- Partial evidence score: **{result['overall_score']:.1f}/100** "
            "(missing rounds count as zero; not a complete interview score)"
        )
    lines = [
        f"# {session['interview_id']} — {session['role_id']}",
        "",
        f"- Status: **{result['completion_status']}**",
        f"- Seniority: `{session['seniority']}`",
        f"- Blueprint: `{session['blueprint_id']}`",
        f"- Difficulty band: `{session['difficulty']}`",
        overall_line,
        "- Practice mastery: **unchanged**",
        "",
        "## Evidence-backed question scores",
        "",
    ]
    if session.get("delivery_mode") == "non_coding_fallback":
        coverage = session["blueprint_coverage"]
        omitted = ", ".join(
            str(value["type"]) for value in coverage["omitted_rounds"]
        )
        lines[5:5] = [
            "- Delivery mode: **non-coding fallback**",
            f"- Blueprint evidence coverage: **{float(coverage['coverage_weight']) * 100:.1f}%**",
            f"- Omitted rounds: **{omitted}** (missing local environment; counted as zero)",
        ]
    for question in session["questions"]:
        question_id = question["question_id"]
        score = result["question_scores"].get(question_id)
        assessment = assessments.get(question_id)
        if assessment is None:
            lines.append(f"- {question_id} {question['title']}: unscored")
            continue
        lines.extend(
            [
                f"### {question_id} {question['title']} — {score:.1f}/100",
                "",
                f"- **Source:** `{assessment['source']}`",
                f"- **Confidence:** `{assessment['confidence']}`",
                f"- **Evidence:** {assessment['evidence']}",
                *(
                    [f"- **Follow-ups:** {', '.join(assessment['followup_ids'])}"]
                    if assessment.get("followup_ids")
                    else []
                ),
                f"- **Recorded at:** `{assessment['recorded_at']}`",
                "",
            ]
        )
    followups = session.get("followups", ())
    if followups:
        lines.extend(["", "## Follow-up records", ""])
        question_titles = {
            question["question_id"]: question["title"]
            for question in session["questions"]
        }
        for followup in followups:
            parent_id = followup["parent_question_id"]
            parent_title = question_titles.get(parent_id, parent_id)
            lines.extend(
                [
                    f"### {followup['followup_id']} — {parent_id} {parent_title}",
                    "",
                    f"- **Prompt:** {followup['prompt']}",
                    f"- **Answer:** {followup['answer']}",
                    f"- **Source:** `{followup['source']}`",
                    f"- **Recorded at:** `{followup['recorded_at']}`",
                    "",
                ]
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
    assessment_evidence = [
        {
            "question_id": question["question_id"],
            "title": question["title"],
            **assessments[question["question_id"]],
            "score": result["question_scores"].get(question["question_id"]),
        }
        for question in session["questions"]
        if question["question_id"] in assessments
    ]
    report_payload = {
        **result,
        "score_scope": score_scope,
        "assessment_evidence": assessment_evidence,
        "followups": list(followups),
    }
    if session.get("delivery_mode") == "non_coding_fallback":
        report_payload["delivery_mode"] = "non_coding_fallback"
        report_payload["blueprint_coverage"] = session["blueprint_coverage"]
    _atomic_write(
        root / "report.json",
        (json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
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
