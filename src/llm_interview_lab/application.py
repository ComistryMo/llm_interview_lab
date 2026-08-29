"""Thin application facade shared by the CLI and desktop client.

Domain rules remain in Catalog, Workspace, Lifecycle, Grader and interview
modules.  This facade only coordinates those operations and returns structured
values suitable for a terminal or a Qt model.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
import importlib.util
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .catalog import Catalog, Problem, load_catalog
from .events import WorkspaceState, append_event, read_events, reduce_events
from .grader import GraderResult, run_public_tests
from .lifecycle import ReviewInput, ReviewResult, record_review
from .materials import add_material, list_materials
from .role_interviews import (
    create_role_interview,
    current_role_question,
    finish_role_interview,
    interview_preflight,
    list_role_interviews,
    load_role_interview,
    record_role_answer,
    record_role_assessment,
    record_role_followup,
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
    profile_id_for_display_name,
    profile_paths,
    ensure_profile_path_is_safe,
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
        display_name: str | None = None,
        role_id: str | None = None,
        seniority: str = "new_grad",
        skill_self_assessment: Mapping[str, int] | None = None,
        ai_mode: str = "disabled",
    ) -> dict[str, Any]:
        configuration = (
            self._validate_role_configuration(
                role_id,
                seniority=seniority,
                skill_self_assessment=skill_self_assessment,
                ai_mode=ai_mode,
            )
            if role_id
            else None
        )
        role = configuration[0] if configuration else None
        result = init_profile(
            self.repo_root,
            profile_id,
            role.required_tracks if role else None,
            display_name=display_name,
        )
        if configuration is not None:
            role, values = configuration
            update_role_preferences(
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
        return {
            "profile_id": profile_id,
            "display_name": load_profile(result.paths, self.repo_root).get(
                "display_name", profile_id
            ),
            "created": result.created,
            "profile": load_profile(result.paths, self.repo_root),
        }

    def initialize_profile_for_display_name(
        self,
        display_name: str,
        *,
        role_id: str | None = None,
        seniority: str = "new_grad",
        skill_self_assessment: Mapping[str, int] | None = None,
        ai_mode: str = "disabled",
    ) -> dict[str, Any]:
        """Initialize a user-facing name while keeping a safe internal id."""

        profile_id = profile_id_for_display_name(self.repo_root, display_name)
        return self.initialize_profile(
            profile_id,
            display_name=display_name,
            role_id=role_id,
            seniority=seniority,
            skill_self_assessment=skill_self_assessment,
            ai_mode=ai_mode,
        )

    def configure_role(
        self,
        profile_id: str,
        role_id: str,
        *,
        seniority: str = "new_grad",
        skill_self_assessment: Mapping[str, int] | None = None,
        ai_mode: str = "disabled",
    ) -> dict[str, Any]:
        role, values = self._validate_role_configuration(
            role_id,
            seniority=seniority,
            skill_self_assessment=skill_self_assessment,
            ai_mode=ai_mode,
        )
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

    def _validate_role_configuration(
        self,
        role_id: str,
        *,
        seniority: str,
        skill_self_assessment: Mapping[str, int] | None,
        ai_mode: str,
    ):
        """Validate onboarding inputs before any Profile file is created."""

        role = self.roles.resolve_role(role_id)
        if seniority not in role.seniority:
            raise ApplicationError(f"unsupported seniority for {role.id}: {seniority}")
        if ai_mode not in {"disabled", "provider", "codex"}:
            raise ApplicationError("AI mode must be disabled, provider, or codex")
        if skill_self_assessment is not None and not isinstance(
            skill_self_assessment, Mapping
        ):
            raise ApplicationError("skill self-assessment must be an object")
        values = dict(skill_self_assessment or {})
        unknown = set(values) - set(self.roles.skills)
        if unknown:
            raise ApplicationError(
                "unknown skill self-assessment: " + ", ".join(sorted(unknown))
            )
        if any(type(value) is not int or value < 0 or value > 4 for value in values.values()):
            raise ApplicationError("skill self-assessment levels must be integers from 0 to 4")
        return role, values

    def role_cards(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for role in self.roles.roles.values():
            top = sorted(
                role.skill_weights,
                key=lambda skill_id: (-role.skill_weights[skill_id].weight, skill_id),
            )[:8]
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

    def material_cards(self, profile_id: str) -> list[dict[str, Any]]:
        """Return manifest metadata only; never read or expose material bodies."""

        return [item.as_dict() for item in list_materials(self.repo_root, profile_id)]

    def add_career_material(
        self,
        profile_id: str,
        source_path: str | Path,
        *,
        kind: str,
        title: str | None = None,
        ai_access: bool = False,
    ) -> dict[str, Any]:
        return add_material(
            self.repo_root,
            profile_id,
            source_path,
            kind=kind,
            title=title,
            ai_access=ai_access,
        ).as_dict()

    def _state(self, profile_id: str):
        paths = profile_paths(self.repo_root, profile_id)
        profile = load_profile(paths, self.repo_root)
        events = read_events(paths.events_file, event_schema_path(self.repo_root))
        return paths, profile, reduce_events(events)

    @staticmethod
    def _current_time(now: datetime | None = None) -> datetime:
        value = now or datetime.now().astimezone()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ApplicationError("application clock must include a timezone")
        return value

    @staticmethod
    def _problem_environment_available(problem: Problem) -> bool:
        interface = problem.raw.get("interface", {})
        framework = interface.get("framework", "") if isinstance(interface, Mapping) else ""
        return str(framework).lower() != "pytorch" or importlib.util.find_spec("torch") is not None

    def practice_actions(
        self, profile_id: str, problem_id: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
        """Derive truthful review and retention actions from canonical events."""

        _, _, state = self._state(profile_id)
        problem = self.catalog.get(problem_id)
        return self._practice_actions_from_state(
            state, problem, self._current_time(now)
        )

    def _practice_actions_from_state(
        self, state: WorkspaceState, problem: Problem, current_time: datetime
    ) -> dict[str, Any]:
        """Derive actions from an already-reduced Profile state."""

        problem_id = problem.id
        reviewed = state.problem_reviewed(problem_id)
        review_state = (
            "complete"
            if reviewed
            else "review_available"
            if state.problem_implemented(problem_id)
            else "blocked"
        )
        actions: dict[str, Any] = {
            "review": {
                "state": review_state,
                "actionable": review_state == "review_available",
                "blocked_reason": (
                    "" if review_state != "blocked" else "先通过公开测试并提交当前实现。"
                ),
            },
            "retention": {},
        }
        for stage in ("d2", "d7"):
            completed = (
                problem_id in state.retained_d2
                if stage == "d2"
                else problem_id in state.retained_d7
            )
            value: dict[str, Any] = {
                "stage": stage,
                "state": "blocked",
                "due_at": "",
                "actionable": False,
                "blocked_reason": "",
            }
            if completed:
                value["state"] = "complete"
            elif not reviewed:
                value["blocked_reason"] = "先完成契约审查与口述答辩。"
            elif stage == "d7" and problem_id not in state.retained_d2:
                value["blocked_reason"] = "先通过 D+2 间隔复测。"
            elif problem.retention_variant(self.repo_root, stage) is None:
                value["state"] = "missing_asset"
                value["blocked_reason"] = f"{stage.upper()} 尚无经过验证的复测资产。"
            elif not self._problem_environment_available(problem):
                value["state"] = "missing_environment"
                value["blocked_reason"] = "当前环境缺少 PyTorch 练习依赖。"
            else:
                due_at = retention_due_at(state, problem_id, stage)
                value["due_at"] = due_at.isoformat()
                existing = next(
                    (
                        attempt
                        for attempt in reversed(state.attempts_for(problem_id))
                        if attempt.retention_stage == stage
                    ),
                    None,
                )
                if existing is not None:
                    value["state"] = "in_progress"
                    value["actionable"] = True
                elif current_time < due_at:
                    value["state"] = "future"
                    value["blocked_reason"] = f"将在 {due_at.isoformat(timespec='seconds')} 到期。"
                else:
                    value["state"] = "due"
                    value["actionable"] = True
            actions["retention"][stage] = value
        return actions

    def dashboard(
        self, profile_id: str, *, now: datetime | None = None
    ) -> dict[str, Any]:
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
        due_retention: list[dict[str, Any]] = []
        current_time = self._current_time(now)
        for problem_id in sorted(state.reviewed_at):
            problem = self.catalog.get(problem_id)
            actions = self._practice_actions_from_state(
                state, problem, current_time
            )
            for stage in ("d2", "d7"):
                action = actions["retention"][stage]
                if action["state"] not in {"due", "in_progress"}:
                    continue
                due_retention.append(
                    {
                        "problem_id": problem_id,
                        "title": problem.title,
                        "stage": stage,
                        "due_at": action["due_at"],
                        "actionable": action["actionable"],
                        "blocked_reason": action["blocked_reason"],
                    }
                )
                break
        due_retention.sort(key=lambda value: (value["due_at"], value["problem_id"]))
        role_readiness: list[dict[str, Any]] = []
        if role_preferences:
            role = self.roles.roles.get(role_preferences.get("primary_role"))
            seniority = role_preferences.get("seniority", "new_grad")
            assessment = role_preferences.get("skill_self_assessment", {})
            if role is not None and seniority in role.seniority:
                domains: dict[str, dict[str, float]] = {}
                for skill_id, target in role.skill_weights.items():
                    skill = self.roles.skills[skill_id]
                    target_level = max(1, target.target_level[seniority])
                    related = set(skill.related_problems)
                    verified_level = (
                        3 * len(related.intersection(state.mastered)) / len(related)
                        if related
                        else 0.0
                    )
                    bucket = domains.setdefault(
                        skill.domain,
                        {"weight": 0.0, "self": 0.0, "verified": 0.0},
                    )
                    bucket["weight"] += target.weight
                    bucket["self"] += target.weight * min(
                        float(assessment.get(skill_id, 0)) / target_level, 1.0
                    )
                    bucket["verified"] += target.weight * min(
                        verified_level / target_level, 1.0
                    )
                role_readiness = [
                    {
                        "id": domain,
                        "label": domain.replace("_", " ").title(),
                        "self_reported": round(value["self"] / value["weight"], 3),
                        "verified": round(value["verified"] / value["weight"], 3),
                    }
                    for domain, value in sorted(domains.items())
                    if value["weight"] > 0
                ]
        role_view = None
        if role_preferences:
            role_view = dict(role_preferences)
            selected_role = self.roles.roles.get(role_preferences.get("primary_role"))
            if selected_role is not None:
                role_view["title"] = selected_role.title
        return {
            "profile_id": profile_id,
            "role": role_view,
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
            "role_readiness": role_readiness,
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

    def problem_cards(self, profile_id: str) -> list[dict[str, Any]]:
        _, profile, state = self._state(profile_id)
        tracks = set(profile["target_roles"])
        role_preferences = profile.get("role_preferences", {})
        role = self.roles.roles.get(role_preferences.get("primary_role"))
        recommended_order: dict[str, int] = {}
        if role is not None:
            for quest_id in role.recommended_quests:
                quest = self.catalog.quests.get(quest_id)
                if quest is None:
                    continue
                for problem_id in quest.problem_ids:
                    recommended_order.setdefault(problem_id, len(recommended_order))
        torch_available = importlib.util.find_spec("torch") is not None
        cards: list[dict[str, Any]] = []
        for problem_id in self.catalog.order:
            problem = self.catalog.problems[problem_id]
            if not tracks.intersection(problem.raw["tracks"]):
                continue
            interface = problem.raw.get("interface")
            framework = interface.get("framework", "") if isinstance(interface, Mapping) else ""
            skills = problem.raw.get("skills", [])
            if not isinstance(skills, list):
                skills = []
            requires_torch = str(framework).lower() == "pytorch"
            environment_available = not requires_torch or torch_available
            cards.append(
                {
                    "problem_id": problem.id,
                    "title": problem.title,
                    "status": state.problem_status(problem.id),
                    "asset_status": problem.status,
                    "validation": problem.validation_level if problem.ready else "planned",
                    "difficulty": problem.raw["difficulty"],
                    "skills": list(skills),
                    "keywords": [problem.id, problem.title, *skills],
                    "recommendable": bool(problem.recommendable),
                    "recommended_rank": recommended_order.get(problem.id, -1),
                    "environment": (
                        "当前可运行"
                        if environment_available
                        else "需要 PyTorch 练习环境"
                    ),
                    "environment_available": environment_available,
                    "locked": not set(problem.prerequisites).issubset(state.mastered),
                    "prerequisites": list(problem.prerequisites),
                    "retention": bool(
                        problem.ready
                        and all(
                            problem.retention_variant(self.repo_root, stage)
                            for stage in ("d2", "d7")
                        )
                    ),
                }
            )
        return cards

    def current_submission(self, profile_id: str) -> dict[str, Any] | None:
        paths, _, state = self._state(profile_id)
        attempt = state.current_attempt()
        if attempt is None or attempt.submission_relpath is None:
            return None
        path = self.repo_root.joinpath(*attempt.submission_relpath.split("/"))
        inspected = inspect_submission(path, paths.submissions_root)
        return {
            "problem_id": attempt.problem_id,
            "attempt_id": attempt.attempt_id,
            "path": str(inspected.path),
            "sha256": inspected.sha256,
            "text": inspected.path.read_text(encoding="utf-8"),
            "last_public_test": attempt.last_public_test,
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
        self,
        profile_id: str,
        problem_id: str,
        stage: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        return asdict(
            start_retention(
                self.repo_root,
                profile_id,
                self.catalog.get(problem_id),
                stage,
                now=now,
            )
        )

    def run_practice_tests(self, profile_id: str, problem_id: str) -> GraderResult:
        return self._run_practice_tests(
            profile_id,
            problem_id,
            expected_attempt_id=None,
            expected_sha256=None,
            operation_id=None,
        )

    def save_practice_submission(
        self,
        profile_id: str,
        problem_id: str,
        text: str,
        *,
        attempt_id: str | None = None,
    ) -> dict[str, Any]:
        """Atomically persist the exact editor contents for one attempt."""

        if not isinstance(text, str):
            raise ApplicationError("submission must be text")
        paths, _, state = self._state(profile_id)
        attempt = state.latest_attempt(problem_id)
        if attempt is None or attempt.submission_relpath is None:
            raise ApplicationError("problem has not been started")
        if attempt_id is not None and attempt.attempt_id != attempt_id:
            raise ApplicationError("attempt changed; reload the current task")
        submission = self.repo_root.joinpath(*attempt.submission_relpath.split("/"))
        temporary: Path | None = None
        try:
            submission = ensure_profile_path_is_safe(
                self.repo_root, profile_id, submission, must_exist=True
            )
            temporary = submission.with_name(f".{submission.name}.{uuid4().hex}.tmp")
            ensure_profile_path_is_safe(self.repo_root, profile_id, temporary)
            with temporary.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, submission)
        except OSError as error:
            raise ApplicationError("submission could not be saved") from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except FileNotFoundError:
                    pass
        inspected = inspect_submission(submission, paths.submissions_root)
        return {
            "problem_id": problem_id,
            "attempt_id": attempt.attempt_id,
            "path": str(inspected.path),
            "sha256": inspected.sha256,
            "text": text,
        }

    def run_practice_tests_for_submission(
        self,
        profile_id: str,
        problem_id: str,
        text: str,
        *,
        attempt_id: str | None = None,
        operation_id: str | None = None,
    ) -> GraderResult:
        saved = self.save_practice_submission(
            profile_id, problem_id, text, attempt_id=attempt_id
        )
        return self._run_practice_tests(
            profile_id,
            problem_id,
            expected_attempt_id=saved["attempt_id"],
            expected_sha256=saved["sha256"],
            operation_id=operation_id,
        )

    def _run_practice_tests(
        self,
        profile_id: str,
        problem_id: str,
        *,
        expected_attempt_id: str | None,
        expected_sha256: str | None,
        operation_id: str | None,
    ) -> GraderResult:
        problem = self.catalog.get(problem_id)
        paths, _, state = self._state(profile_id)
        attempt = state.latest_attempt(problem_id)
        if attempt is None or attempt.submission_relpath is None:
            raise ApplicationError("problem has not been started")
        if expected_attempt_id is not None and attempt.attempt_id != expected_attempt_id:
            raise ApplicationError("attempt changed while preparing tests")
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
        # Do not silently associate a result with newer editor contents.
        current_sha = inspect_submission(submission, paths.submissions_root).sha256
        if expected_sha256 is not None and current_sha != expected_sha256:
            result = replace(result, stale=True)
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
                **({"operation_id": operation_id} if operation_id else {}),
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

    def interview_configuration(
        self, role_id: str, seniority: str, difficulty: str
    ) -> dict[str, Any]:
        """Describe whether every blueprint round has a strict local candidate."""

        return interview_preflight(
            self.repo_root,
            self.catalog,
            self.roles,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
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

    def current_interview_coding_submission(
        self, profile_id: str, interview_id: str
    ) -> dict[str, str]:
        """Return only the active coding answer from this exact Profile/session."""

        current = self.current_interview(profile_id, interview_id)["question"]
        if current is None or current["kind"] != "coding":
            raise ApplicationError("the current interview question is not coding")
        paths = profile_paths(self.repo_root, profile_id)
        root = paths.interviews_root / interview_id / "coding" / current["question_id"]
        path = ensure_profile_path_is_safe(
            self.repo_root, profile_id, root / "submission.py", must_exist=True
        )
        inspected = inspect_submission(path, root)
        return {
            "question_id": current["question_id"],
            "sha256": inspected.sha256,
            "text": path.read_text(encoding="utf-8"),
        }

    def save_interview_coding_submission(
        self, profile_id: str, interview_id: str, text: str
    ) -> dict[str, str]:
        """Atomically save the visible active coding answer; never touch Practice."""

        if not isinstance(text, str) or len(text.encode("utf-8")) > 1_000_000:
            raise ApplicationError("coding submission must be UTF-8 text up to 1 MB")
        current = self.current_interview(profile_id, interview_id)["question"]
        if current is None or current["kind"] != "coding":
            raise ApplicationError("the current interview question is not coding")
        paths = profile_paths(self.repo_root, profile_id)
        root = paths.interviews_root / interview_id / "coding" / current["question_id"]
        path = ensure_profile_path_is_safe(
            self.repo_root, profile_id, root / "submission.py", must_exist=True
        )
        temporary = ensure_profile_path_is_safe(
            self.repo_root,
            profile_id,
            path.with_name(f".{path.name}.{uuid4().hex}.tmp"),
        )
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise ApplicationError("coding submission could not be saved") from error
        inspected = inspect_submission(path, root)
        return {
            "question_id": current["question_id"],
            "sha256": inspected.sha256,
            "text": text,
        }

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

    def record_interview_followup(
        self,
        profile_id: str,
        interview_id: str,
        *,
        parent_question_id: str,
        prompt: str,
        answer: str,
        source: str = "ai",
    ) -> dict[str, Any]:
        return record_role_followup(
            self.repo_root,
            profile_id,
            interview_id,
            parent_question_id=parent_question_id,
            prompt=prompt,
            answer=answer,
            source=source,
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

    def resumable_interview(self, profile_id: str) -> dict[str, Any] | None:
        """Return the newest active role interview for one selected Profile."""

        active = [
            session
            for session in list_role_interviews(self.repo_root, profile_id)
            if session["status"] == "active"
        ]
        return active[-1] if active else None

    def interview_result_view(
        self, profile_id: str, interview_id: str
    ) -> dict[str, Any] | None:
        """Regenerate a presentation view from canonical ``session.result``."""

        session = load_role_interview(self.repo_root, profile_id, interview_id)
        result = session.get("result")
        if not isinstance(result, Mapping):
            return None
        assessment_evidence = []
        for question in session["questions"]:
            question_id = question["question_id"]
            assessment = session["assessments"].get(question_id)
            if not isinstance(assessment, Mapping):
                continue
            assessment_evidence.append(
                {
                    "question_id": question_id,
                    "title": question["title"],
                    "source": assessment["source"],
                    "evidence": assessment["evidence"],
                    "confidence": assessment["confidence"],
                    "score": result["question_scores"].get(question_id),
                }
            )
        return {
            "interview_id": interview_id,
            "status": session["status"],
            "role_id": session["role_id"],
            "seniority": session["seniority"],
            "difficulty": session["difficulty"],
            "completion_status": result["completion_status"],
            "overall_score": result["overall_score"],
            "question_scores": dict(result["question_scores"]),
            "assessment_evidence": assessment_evidence,
            "skill_scores": dict(result["skill_scores"]),
            "critical_gaps": list(result["critical_gaps"]),
            "unanswered": list(result["unanswered"]),
            "unscored": list(result["unscored"]),
            "summary": result["summary"],
            "finished_at": result["finished_at"],
        }

    def recent_interview_result(self, profile_id: str) -> dict[str, Any] | None:
        """Return the newest completed/incomplete result after active recovery."""

        sessions = list_role_interviews(self.repo_root, profile_id)
        for session in reversed(sessions):
            if session["status"] in {"completed", "incomplete"} and session["result"] is not None:
                return self.interview_result_view(profile_id, session["interview_id"])
        return None

    def preferred_interview(self, profile_id: str) -> dict[str, Any] | None:
        """Prefer active recovery, otherwise expose the newest canonical result."""

        active = self.resumable_interview(profile_id)
        if active is not None:
            return {"kind": "active", "interview_id": active["interview_id"]}
        result = self.recent_interview_result(profile_id)
        if result is not None:
            return {"kind": "result", **result}
        return None
