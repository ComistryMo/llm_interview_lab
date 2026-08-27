"""Thin application facade shared by the CLI and desktop client.

Domain rules remain in Catalog, Workspace, Lifecycle, Grader and interview
modules.  This facade only coordinates those operations and returns structured
values suitable for a terminal or a Qt model.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from .catalog import Catalog, Problem, load_catalog
from .events import append_event, read_events, reduce_events
from .grader import GraderResult, run_public_tests
from .lifecycle import ReviewInput, ReviewResult, record_review
from .role_interviews import (
    create_role_interview,
    current_role_question,
    finish_role_interview,
    load_role_interview,
    record_role_answer,
    record_role_assessment,
    role_interview_report,
    run_role_coding_test,
    start_role_interview,
)
from .roles import RoleCatalog, load_role_catalog
from .submissions import inspect_submission
from .workspace import (
    event_schema_path,
    find_repository_root,
    init_profile,
    load_profile,
    profile_paths,
    retention_due_at,
    start_problem,
    start_retention,
    update_role_preferences,
)


class ApplicationError(RuntimeError):
    """Raised when a user-facing application operation cannot proceed."""


class ApplicationService:
    """Repository-local use cases with no dependency on CLI or GUI code."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or find_repository_root()).resolve()
        self.catalog: Catalog = load_catalog(self.repo_root)
        self.roles: RoleCatalog = load_role_catalog(
            self.repo_root, curriculum=self.catalog
        )

    def initialize_profile(
        self,
        profile_id: str = "default",
        *,
        role_id: str | None = None,
        seniority: str = "new_grad",
        skill_self_assessment: Mapping[str, int] | None = None,
        ai_mode: str = "disabled",
    ) -> dict[str, Any]:
        role = self.roles.resolve_role(role_id) if role_id else None
        result = init_profile(
            self.repo_root,
            profile_id,
            role.required_tracks if role else None,
        )
        if role is not None:
            self.configure_role(
                profile_id,
                role.id,
                seniority=seniority,
                skill_self_assessment=skill_self_assessment or {},
                ai_mode=ai_mode,
            )
        return {
            "profile_id": profile_id,
            "created": result.created,
            "profile": load_profile(result.paths, self.repo_root),
        }

    def configure_role(
        self,
        profile_id: str,
        role_id: str,
        *,
        seniority: str = "new_grad",
        skill_self_assessment: Mapping[str, int] | None = None,
        ai_mode: str = "disabled",
    ) -> dict[str, Any]:
        role = self.roles.resolve_role(role_id)
        if seniority not in role.seniority:
            raise ApplicationError(f"unsupported seniority for {role.id}: {seniority}")
        if ai_mode not in {"disabled", "provider", "codex"}:
            raise ApplicationError("AI mode must be disabled, provider, or codex")
        values = dict(skill_self_assessment or {})
        unknown = set(values) - set(self.roles.skills)
        if unknown:
            raise ApplicationError(
                "unknown skill self-assessment: " + ", ".join(sorted(unknown))
            )
        if any(type(value) is not int or value < 0 or value > 4 for value in values.values()):
            raise ApplicationError("skill self-assessment levels must be integers from 0 to 4")
        return update_role_preferences(
            self.repo_root,
            profile_id,
            {
                "primary_role": role.id,
                "seniority": seniority,
                "skill_self_assessment": values,
                "ai_mode": ai_mode,
            },
            target_roles=role.required_tracks,
        )

    def role_cards(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for role in self.roles.roles.values():
            top = sorted(
                role.skill_weights,
                key=lambda skill_id: (-role.skill_weights[skill_id].weight, skill_id),
            )[:4]
            cards.append(
                {
                    "id": role.id,
                    "title": role.title,
                    "summary": role.summary,
                    "aliases": list(role.aliases),
                    "top_skills": [
                        {"id": skill_id, "title": self.roles.skills[skill_id].title}
                        for skill_id in top
                    ],
                }
            )
        return cards

    def _state(self, profile_id: str):
        paths = profile_paths(self.repo_root, profile_id)
        profile = load_profile(paths, self.repo_root)
        events = read_events(paths.events_file, event_schema_path(self.repo_root))
        return paths, profile, reduce_events(events)

    def dashboard(self, profile_id: str) -> dict[str, Any]:
        _, profile, state = self._state(profile_id)
        current = state.current_attempt()
        if current is not None and state.problem_status(current.problem_id) == "mastered":
            current = None
        role_preferences = profile.get("role_preferences", {})
        quest_ids: tuple[str, ...] = ()
        if role_preferences:
            role = self.roles.roles.get(role_preferences.get("primary_role"))
            if role is not None:
                quest_ids = role.recommended_quests
        available = [
            problem
            for problem in self.catalog.unlocked(
                state.mastered,
                set(profile["target_roles"]),
                include_experimental=bool(
                    profile["preferences"].get("allow_experimental_problems", False)
                ),
            )
            if state.problem_status(problem.id) == "not_started"
        ]
        due_review = [
            attempt.problem_id
            for attempt in state.attempts.values()
            if attempt.implemented and not attempt.reviewed
        ]
        due_retention: list[dict[str, str]] = []
        for problem_id in sorted(state.reviewed):
            if problem_id not in state.retained_d2:
                due_retention.append(
                    {"problem_id": problem_id, "stage": "d2", "due_at": retention_due_at(state, problem_id, "d2").isoformat()}
                )
            elif problem_id not in state.retained_d7:
                due_retention.append(
                    {"problem_id": problem_id, "stage": "d7", "due_at": retention_due_at(state, problem_id, "d7").isoformat()}
                )
        return {
            "profile_id": profile_id,
            "role": role_preferences or None,
            "current": (
                {
                    "problem_id": current.problem_id,
                    "title": self.catalog.get(current.problem_id).title,
                    "status": state.problem_status(current.problem_id),
                }
                if current
                else None
            ),
            "recommended_quests": [
                {"id": quest_id, "title": self.catalog.quests[quest_id].title}
                for quest_id in quest_ids
                if quest_id in self.catalog.quests
            ],
            "due_review": due_review[:3],
            "due_retention": due_retention[:3],
            "unlocks": [
                {"problem_id": problem.id, "title": problem.title}
                for problem in available[:3]
            ],
            "mastered_count": len(state.mastered),
        }

    def problem_view(self, problem_id: str) -> dict[str, Any]:
        problem = self.catalog.get(problem_id)
        task = None
        if problem.problem_dir is not None:
            task = (problem.problem_dir / "task.md").read_text(encoding="utf-8")
        return {
            "problem_id": problem.id,
            "title": problem.title,
            "status": problem.status,
            "validation": problem.validation_level if problem.ready else None,
            "prerequisites": list(problem.prerequisites),
            "difficulty": problem.raw["difficulty"],
            "task": task,
        }

    def start_practice(
        self, profile_id: str, problem_id: str, *, allow_experimental: bool = False
    ) -> dict[str, Any]:
        problem = self.catalog.get(problem_id)
        if not problem.ready:
            raise ApplicationError("planned problems cannot be started")
        _, profile, state = self._state(profile_id)
        if not problem.recommendable and not (
            allow_experimental
            or profile["preferences"].get("allow_experimental_problems", False)
        ):
            raise ApplicationError("contract-only problem requires experimental opt-in")
        missing = sorted(set(problem.prerequisites) - state.mastered)
        if missing:
            raise ApplicationError("prerequisites are not mastered: " + ", ".join(missing))
        return asdict(start_problem(self.repo_root, profile_id, problem))

    def start_retention(
        self, profile_id: str, problem_id: str, stage: str
    ) -> dict[str, Any]:
        return asdict(
            start_retention(self.repo_root, profile_id, self.catalog.get(problem_id), stage)
        )

    def run_practice_tests(self, profile_id: str, problem_id: str) -> GraderResult:
        problem = self.catalog.get(problem_id)
        paths, _, state = self._state(profile_id)
        attempt = state.latest_attempt(problem_id)
        if attempt is None or attempt.submission_relpath is None:
            raise ApplicationError("problem has not been started")
        test_path, symbol = problem.public_tests, problem.symbol
        if attempt.retention_stage:
            variant = problem.retention_variant(self.repo_root, attempt.retention_stage)
            if variant is None or not attempt.retention_verified:
                raise ApplicationError("verified retention assets are unavailable")
            _, test_path, symbol = variant
        assert test_path is not None and symbol is not None
        submission = self.repo_root.joinpath(*attempt.submission_relpath.split("/"))
        result = run_public_tests(
            repo_root=self.repo_root,
            test_path=test_path,
            submission_path=submission,
            submissions_root=paths.submissions_root,
            expected_symbol=symbol,
            time_limit_ms=problem.time_limit_ms,
            output_limit_kb=problem.output_limit_kb,
        )
        append_event(
            paths.events_file,
            event_schema_path(self.repo_root),
            profile_id=profile_id,
            event_type="public_tests_run",
            problem_id=problem_id,
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
        return result

    def submit_practice(self, profile_id: str, problem_id: str) -> dict[str, Any]:
        paths, _, state = self._state(profile_id)
        attempt = state.latest_attempt(problem_id)
        if attempt is None or attempt.submission_relpath is None:
            raise ApplicationError("problem has not been started")
        submission = self.repo_root.joinpath(*attempt.submission_relpath.split("/"))
        inspected = inspect_submission(submission, paths.submissions_root)
        passed = bool(
            attempt.last_public_test
            and attempt.last_public_test["status"] == "passed"
            and attempt.last_public_test["submission_sha256"] == inspected.sha256
        )
        append_event(
            paths.events_file,
            event_schema_path(self.repo_root),
            profile_id=profile_id,
            event_type="submission_created",
            problem_id=problem_id,
            attempt_id=attempt.attempt_id,
            payload={
                "submission_sha256": inspected.sha256,
                "public_tests_current_and_passed": passed,
            },
        )
        if passed:
            append_event(
                paths.events_file,
                event_schema_path(self.repo_root),
                profile_id=profile_id,
                event_type="task_implemented",
                problem_id=problem_id,
                attempt_id=attempt.attempt_id,
                payload={"submission_sha256": inspected.sha256},
            )
        return {"implemented": passed, "submission_sha256": inspected.sha256}

    def review_practice(
        self, profile_id: str, problem_id: str, review: ReviewInput
    ) -> ReviewResult:
        return record_review(self.repo_root, profile_id, problem_id, review)

    def create_interview(
        self,
        profile_id: str,
        *,
        role_id: str,
        seniority: str = "new_grad",
        difficulty: str = "medium",
        ai_mode: str = "disabled",
        material_ids: Iterable[str] = (),
        consent_materials: bool = False,
        seed: int = 0,
    ) -> dict[str, Any]:
        return create_role_interview(
            self.repo_root,
            profile_id,
            self.catalog,
            self.roles,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
            ai_mode=ai_mode,
            material_ids=material_ids,
            consent_materials=consent_materials,
            seed=seed,
        )

    def start_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return start_role_interview(
            self.repo_root, profile_id, interview_id, self.catalog
        )

    def current_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return current_role_question(self.repo_root, profile_id, interview_id)

    def answer_interview(
        self, profile_id: str, interview_id: str, question_id: str, answer: str
    ) -> dict[str, Any]:
        return record_role_answer(
            self.repo_root, profile_id, interview_id, question_id, answer
        )

    def test_interview_coding(
        self, profile_id: str, interview_id: str
    ) -> GraderResult:
        return run_role_coding_test(
            self.repo_root, profile_id, interview_id, self.catalog
        )

    def score_interview(
        self,
        profile_id: str,
        interview_id: str,
        question_id: str,
        scores: Mapping[str, int],
        *,
        evidence: str,
        source: str,
        confidence: str,
        fatal_issues: Iterable[str] = (),
    ) -> dict[str, Any]:
        return record_role_assessment(
            self.repo_root,
            profile_id,
            interview_id,
            question_id,
            scores,
            evidence=evidence,
            source=source,
            confidence=confidence,
            fatal_issues=fatal_issues,
        )

    def finish_interview(
        self,
        profile_id: str,
        interview_id: str,
        *,
        summary: str = "",
        confirm_incomplete: bool = False,
    ) -> dict[str, Any]:
        return finish_role_interview(
            self.repo_root,
            profile_id,
            interview_id,
            summary=summary,
            confirm_incomplete=confirm_incomplete,
        )

    def interview_report(
        self, profile_id: str, interview_id: str, *, format_name: str = "markdown"
    ) -> str:
        return role_interview_report(
            self.repo_root, profile_id, interview_id, format_name=format_name
        )

    def interview_session(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return load_role_interview(self.repo_root, profile_id, interview_id)
