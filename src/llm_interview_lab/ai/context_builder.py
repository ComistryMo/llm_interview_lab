"""Explicit, previewable context assembly for remote chat providers."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from .base import ContextPart, ContextPreview
from ..catalog import Catalog
from ..events import read_events, reduce_events
from ..materials import MaterialError, get_material, resolve_material_path
from ..role_interviews import current_role_question, load_role_interview
from ..submissions import inspect_submission
from ..workspace import event_schema_path, load_profile, profile_paths


class ContextBuilderError(RuntimeError):
    """Raised when requested context is unavailable or outside the current task."""


def _part(identifier: str, label: str, content: str, *, sensitive: bool = False) -> ContextPart:
    return ContextPart(
        identifier,
        label,
        content,
        hashlib.sha256(content.encode("utf-8")).hexdigest(),
        True,
        sensitive,
    )


def build_practice_context_preview(
    repo_root: Path,
    catalog: Catalog,
    profile_id: str,
    *,
    mode: str,
    help_level: str | None = None,
    include_submission: bool = False,
    include_test_output: bool = True,
) -> ContextPreview:
    """Build only the current Practice context; never enumerate a Profile."""

    if mode not in {"coach", "teacher", "reviewer"}:
        raise ContextBuilderError("mode must be coach, teacher, or reviewer")
    if mode == "teacher" and help_level not in {"H1", "H2", "H3"}:
        raise ContextBuilderError("teacher mode requires H1, H2, or H3")
    if mode != "teacher" and help_level is not None:
        raise ContextBuilderError("help level is available only in teacher mode")
    paths = profile_paths(repo_root, profile_id)
    profile = load_profile(paths, repo_root)
    state = reduce_events(read_events(paths.events_file, event_schema_path(repo_root)))
    attempt = state.current_attempt()
    if attempt is None:
        raise ContextBuilderError("current Practice task is unavailable")
    problem = catalog.get(attempt.problem_id)
    assert problem.problem_dir is not None
    task = (problem.problem_dir / "task.md").read_text(encoding="utf-8")
    policy = (
        f"Mode={mode.upper()}; profile={profile_id}. Never modify the learner submission. "
        "Public tests do not grant mastery. Follow coach/POLICY.md and the H0-H5 policy."
    )
    parts = [
        _part("policy", "AI policy", policy),
        _part("task", f"Current task — {problem.id} {problem.title}", task),
    ]
    role = profile.get("role_preferences")
    if role:
        parts.append(
            _part(
                "role",
                "Target role",
                f"role={role['primary_role']} seniority={role['seniority']}",
            )
        )
    if mode == "teacher":
        hints = (problem.problem_dir / "hints.md").read_text(encoding="utf-8")
        marker = f"## {help_level}"
        selected = hints.split(marker, 1)[1].split("\n## ", 1)[0].strip() if marker in hints else ""
        parts.append(_part("hint", f"Allowed hint {help_level}", selected))
    if include_submission:
        if attempt.submission_relpath is None:
            raise ContextBuilderError("current attempt has no submission")
        submission = repo_root.joinpath(*attempt.submission_relpath.split("/"))
        inspected = inspect_submission(submission, paths.submissions_root)
        parts.append(
            _part(
                "submission",
                "Selected current submission",
                inspected.path.read_text(encoding="utf-8"),
                sensitive=True,
            )
        )
    if include_test_output and attempt.last_public_test:
        evidence = attempt.last_public_test
        parts.append(
            _part(
                "test",
                "Latest public test summary",
                (
                    f"status={evidence['status']} passed={evidence['passed']} "
                    f"failed={evidence['failed']} duration_ms={evidence['duration_ms']}"
                ),
            )
        )
    return ContextPreview(mode, profile_id, tuple(parts))


def build_role_interview_context_preview(
    repo_root: Path,
    profile_id: str,
    interview_id: str,
    *,
    candidate_answer: str | None = None,
    include_materials: bool = True,
    now: datetime | None = None,
) -> ContextPreview:
    """Build one current-question interview context from frozen, consented facts."""

    session = load_role_interview(repo_root, profile_id, interview_id)
    if session["ai_mode"] == "disabled":
        raise ContextBuilderError("this interview was created without AI access")
    current = current_role_question(repo_root, profile_id, interview_id, now=now)
    question = current["question"]
    if question is None:
        raise ContextBuilderError("the interview has no unanswered question")
    policy = (
        "Mode=INTERVIEWER. Ask or assess only the frozen current question. "
        "Do not teach, edit a submission, invent career facts, grant Practice mastery, "
        "or output an offer probability. Separate evidence, inference, and uncertainty."
    )
    contract = (
        f"role={session['role_id']} seniority={session['seniority']} "
        f"difficulty={session['difficulty']} question_id={question['question_id']}\n"
        f"kind={question['kind']} skills={','.join(question['skills'])}\n\n"
        f"{question['prompt']}\n\nRubric:\n{question['rubric']}"
    )
    parts = [
        _part("policy", "Interviewer policy", policy),
        _part("question", "Frozen current question and rubric", contract),
    ]
    for reference in session["material_refs"] if include_materials else ():
        if reference["allowed_use"] != "role_interview":
            raise ContextBuilderError("interview material has an invalid consent purpose")
        try:
            material = get_material(repo_root, profile_id, reference["id"])
            if not material.ai_access or material.sha256 != reference["sha256"]:
                raise ContextBuilderError(
                    f"material consent is stale or revoked: {reference['id']}"
                )
            path = resolve_material_path(repo_root, profile_id, material)
        except MaterialError as error:
            raise ContextBuilderError(
                f"material consent is stale or revoked: {reference['id']}"
            ) from error
        parts.append(
            _part(
                f"material:{material.id}",
                f"Consented {material.kind}: {material.title}",
                path.read_text(encoding="utf-8"),
                sensitive=True,
            )
        )
    if candidate_answer is not None:
        if not candidate_answer.strip() or len(candidate_answer) > 50_000:
            raise ContextBuilderError("candidate answer must contain 1 to 50000 characters")
        parts.append(
            _part(
                "candidate_answer",
                "Candidate answer",
                candidate_answer.strip(),
                sensitive=True,
            )
        )
    return ContextPreview("interviewer", profile_id, tuple(parts))
