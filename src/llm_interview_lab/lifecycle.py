"""Deterministic review and retention transitions for one local Profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .events import append_event, read_events, reduce_events
from .submissions import inspect_submission
from .workspace import event_schema_path, load_profile, profile_paths


class LifecycleError(RuntimeError):
    """Raised when evidence does not permit a requested transition."""


@dataclass(frozen=True)
class ReviewInput:
    contract_status: str
    oral_status: str
    code_explanation: str
    complexity: str
    boundary_conditions: str


@dataclass(frozen=True)
class ReviewResult:
    status: str
    mastered: bool
    appended: bool


def record_review(
    repo_root: Path,
    profile_id: str,
    problem_id: str,
    review: ReviewInput,
    *,
    timestamp: datetime | None = None,
) -> ReviewResult:
    """Record structured review evidence; never accepts a direct mastery flag."""

    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    schema = event_schema_path(repo_root)
    state = reduce_events(read_events(paths.events_file, schema))
    attempt = state.latest_attempt(problem_id)
    if attempt is None or attempt.submission_relpath is None:
        raise LifecycleError(f"problem is not started: {problem_id}")
    if not attempt.implemented or attempt.implemented_sha256 is None:
        raise LifecycleError("submit a passing implementation before review")
    submission = repo_root.joinpath(*attempt.submission_relpath.split("/"))
    inspected = inspect_submission(submission, paths.submissions_root)
    if inspected.sha256 != attempt.implemented_sha256:
        raise LifecycleError("submission changed after implementation; rerun test and submit")
    payload = {
        "submission_sha256": inspected.sha256,
        "contract_status": review.contract_status,
        "oral_status": review.oral_status,
        "code_explanation": review.code_explanation,
        "complexity": review.complexity,
        "boundary_conditions": review.boundary_conditions,
    }
    reviewed = append_event(
        paths.events_file, schema, profile_id=profile_id, event_type="review_completed",
        problem_id=problem_id, attempt_id=attempt.attempt_id, payload=payload, timestamp=timestamp,
    )
    passed = review.contract_status == review.oral_status == "passed"
    if not passed:
        return ReviewResult("implemented", False, reviewed.appended)
    if attempt.retention_stage is None:
        return ReviewResult("reviewed", False, reviewed.appended)
    retention_type = f"retention_{attempt.retention_stage}_passed"
    append_event(
        paths.events_file, schema, profile_id=profile_id, event_type=retention_type,
        problem_id=problem_id, attempt_id=attempt.attempt_id,
        payload={"submission_sha256": inspected.sha256}, timestamp=timestamp,
    )
    if attempt.retention_stage == "d2":
        return ReviewResult("retained_d2", False, reviewed.appended)
    refreshed = reduce_events(read_events(paths.events_file, schema))
    if not refreshed.problem_reviewed(problem_id) or problem_id not in refreshed.retained_d2:
        raise LifecycleError("mastery prerequisites are incomplete")
    append_event(
        paths.events_file, schema, profile_id=profile_id, event_type="task_mastered",
        problem_id=problem_id, attempt_id=attempt.attempt_id,
        payload={"submission_sha256": inspected.sha256}, timestamp=timestamp,
    )
    return ReviewResult("mastered", True, reviewed.appended)
