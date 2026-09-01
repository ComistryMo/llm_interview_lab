"""Thin application facade shared by the CLI and desktop client.

Domain rules remain in Catalog, Workspace, Lifecycle, Grader and interview
modules.  This facade only coordinates those operations and returns structured
values suitable for a terminal or a Qt model.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, replace
from datetime import datetime
import hashlib
import importlib.util
import os
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from .catalog import Catalog, Problem, load_catalog
from .events import WorkspaceState, append_event, read_events, reduce_events
from .grader import GraderResult, run_public_tests
from .knowledge import KnowledgeCard, KnowledgeCatalog, KnowledgeError, load_knowledge
from .lifecycle import ReviewInput, ReviewResult, record_review
from .materials import add_material, list_materials, set_material_ai_access
from .ai.context_builder import build_role_interview_plan_context_preview
from .role_interviews import (
    RoleInterviewError,
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
    role_interview_answer_text,
    run_role_coding_test,
    start_role_interview,
    pause_role_interview,
    preview_personalized_role_interview,
    resume_role_interview,
    role_interview_state,
)
from .roles import RoleCatalog, RoleProfile, load_role_catalog
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


_DOMAIN_LABELS_ZH = {
    "programming_algorithms": "编程与算法",
    "python_engineering": "Python 工程",
    "machine_learning_math": "机器学习数学",
    "deep_learning": "深度学习",
    "llm_vlm": "LLM / VLM",
    "post_training_rl": "后训练与强化学习",
    "agent_application": "Agent 应用",
    "ai_product": "AI 产品",
    "evaluation_safety": "评测与安全",
    "data_mlops": "数据与 MLOps",
    "training_infra": "训练基础设施",
    "inference_systems": "推理系统",
    "system_design": "系统设计",
    "product_communication": "产品沟通",
    "project_deep_dive": "项目深挖",
    "behavioral": "行为面试",
}


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
        # Interview knowledge is intentionally loaded on first use.  The
        # Practice/role views above are needed by the existing application
        # lifecycle, while the public knowledge bundle is an optional,
        # read-only surface and may be absent in older/fixture repositories.
        self._knowledge_catalog: KnowledgeCatalog | None = None
        self._knowledge_curriculum_checked = False

    def knowledge_catalog(
        self,
        *,
        validate_curriculum: bool = True,
        reload: bool = False,
    ) -> KnowledgeCatalog:
        """Return the validated interview knowledge catalog, loading lazily.

        ``KnowledgeCatalog`` is kept separate from the executable Practice
        ``Catalog``.  By default related problem IDs are checked against the
        current Practice catalog; callers that only need schema/source
        validation can pass ``validate_curriculum=False``.  ``reload`` is
        useful for a long-lived desktop process after an author edits the
        fixed YAML file and does not mutate any learner Profile state.
        """

        needs_curriculum_check = (
            validate_curriculum and not self._knowledge_curriculum_checked
        )
        if self._knowledge_catalog is None or reload or needs_curriculum_check:
            curriculum = self.catalog if validate_curriculum else None
            try:
                self._knowledge_catalog = load_knowledge(
                    self.repo_root,
                    curriculum=curriculum,
                )
                self._knowledge_curriculum_checked = validate_curriculum
            except KnowledgeError:
                # Preserve the domain-specific error for callers that want
                # to distinguish malformed public content from a Practice
                # or Profile failure.  CLI boundaries catch this explicitly.
                raise
        return self._knowledge_catalog

    # Explicit loader spelling for callers that use the repository's
    # ``load_*`` naming convention.  It remains lazy and shares the cache.
    def load_knowledge(
        self,
        *,
        validate_curriculum: bool = True,
        reload: bool = False,
    ) -> KnowledgeCatalog:
        return self.knowledge_catalog(
            validate_curriculum=validate_curriculum,
            reload=reload,
        )

    @property
    def knowledge(self) -> KnowledgeCatalog:
        """Convenience property for clients that prefer attribute access."""

        return self.knowledge_catalog()

    @staticmethod
    def _knowledge_search_text(card: KnowledgeCard) -> str:
        """Build a bounded case-folded search document from public card data."""

        # ``raw`` retains additive schema fields authored by future bundles;
        # falling back to the dataclass fields keeps synthetic test cards
        # searchable as well.
        raw = getattr(card, "raw", None)

        def flatten(value: Any) -> Iterable[str]:
            if isinstance(value, Mapping):
                for key, item in value.items():
                    yield str(key)
                    yield from flatten(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    yield from flatten(item)
            elif isinstance(value, set):
                for item in sorted(value, key=lambda item: str(item)):
                    yield from flatten(item)
            elif value is not None:
                yield str(value)

        if isinstance(raw, Mapping) and raw:
            return " ".join(flatten(raw)).casefold()
        return " ".join(
            flatten(
                {
                    "id": card.id,
                    "kind": card.kind,
                    "title": card.title,
                    "domain": card.domain,
                    "tracks": card.tracks,
                    "skills": card.skills,
                    "prompt": card.prompt,
                    "answer_outline": card.answer_outline,
                    "follow_ups": card.follow_ups,
                    "pitfalls": card.pitfalls,
                }
            )
        ).casefold()

    def search_knowledge(
        self,
        query: str | None = None,
        *,
        kind: str | None = None,
        track: str | None = None,
        skill: str | None = None,
        seniority: str | None = None,
        priority: str | None = None,
        role_id: str | None = None,
        role: str | None = None,
        limit: int | None = None,
        validate_curriculum: bool = True,
    ) -> list[KnowledgeCard]:
        """Search public knowledge cards with deterministic, exact filters.

        Query terms are split on whitespace and matched case-insensitively
        against the card's public fields.  All terms must occur (AND
        semantics), while filter order remains the authored YAML order.
        A role matches cards on its required tracks or weighted skills; an
        explicit ``skill`` filter is also a deliberate narrow override.
        ``limit`` is applied after filtering and must be positive when set.
        """

        if limit is not None and (type(limit) is not int or limit <= 0):
            raise ApplicationError("knowledge result limit must be a positive integer")
        if query is not None and not isinstance(query, str):
            raise ApplicationError("knowledge search query must be text")
        if role is not None:
            if role_id is not None and role_id != role:
                raise ApplicationError("knowledge role was supplied twice with different values")
            role_id = role
        if role_id is not None and not isinstance(role_id, str):
            raise ApplicationError("knowledge role must be text")
        cards = self.knowledge_catalog(
            validate_curriculum=validate_curriculum
        ).select(
            kind=kind,
            track=track,
            skill=skill,
            seniority=seniority,
            priority=priority,
        )
        if role_id is not None:
            role_profile = self.roles.resolve_role(role_id)
            allowed_tracks = set(role_profile.required_tracks)
            allowed_skills = set(role_profile.skill_weights)
            explicit_skill = skill
            cards = tuple(
                card
                for card in cards
                if (
                    allowed_tracks.intersection(card.tracks)
                    or allowed_skills.intersection(card.skills)
                    or (explicit_skill is not None and explicit_skill in card.skills)
                )
            )
        terms = tuple(part.casefold() for part in (query or "").split() if part)
        if terms:
            cards = tuple(
                card
                for card in cards
                if all(term in self._knowledge_search_text(card) for term in terms)
            )
        result = list(cards)
        return result[:limit] if limit is not None else result

    def knowledge_items(self, **filters: Any) -> list[KnowledgeCard]:
        """Alias returning card objects for generic catalog consumers."""

        return self.search_knowledge(**filters)

    @staticmethod
    def _knowledge_summary(card: KnowledgeCard) -> dict[str, Any]:
        """Build the compact card shape consumed by list-oriented clients."""

        value: dict[str, Any] = {
            "id": card.id,
            "kind": card.kind,
            "title": card.title,
            "domain": card.domain,
            "tracks": list(card.tracks),
            "skills": list(card.skills),
            "priority": card.priority,
            "difficulty": dict(card.difficulty),
            "seniority": list(card.seniority),
            "related_problems": list(card.related_problems),
            "reviewed_at": card.reviewed_at,
        }
        if card.one_liner:
            value["one_liner"] = card.one_liner
        return value

    @staticmethod
    def _knowledge_payload(card: KnowledgeCard) -> dict[str, Any]:
        """Return a detached full card mapping while preserving future fields."""

        raw = getattr(card, "raw", None)
        if isinstance(raw, Mapping) and raw:
            return copy.deepcopy(dict(raw))
        value = ApplicationService._knowledge_summary(card)
        value.update(
            {
                "prompt": card.prompt,
                "answer_outline": list(card.answer_outline),
                "follow_ups": list(card.follow_ups),
                "pitfalls": list(card.pitfalls),
                "signals": list(card.signals),
                "source_claims": [claim.as_dict() for claim in card.source_claims],
            }
        )
        return value

    def _knowledge_payload_with_sources(
        self,
        card: KnowledgeCard,
        *,
        validate_curriculum: bool = True,
    ) -> dict[str, Any]:
        """Add resolved source records to a detached card payload."""

        payload = self._knowledge_payload(card)
        catalog = self.knowledge_catalog(validate_curriculum=validate_curriculum)
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for claim in card.source_claims:
            if claim.source_id in seen:
                continue
            seen.add(claim.source_id)
            source = catalog.sources.get(claim.source_id)
            if source is not None:
                records.append(source.as_dict())
        payload["source_records"] = records
        return payload

    def knowledge_cards(
        self,
        query: str | None = None,
        *,
        kind: str | None = None,
        track: str | None = None,
        skill: str | None = None,
        seniority: str | None = None,
        priority: str | None = None,
        role_id: str | None = None,
        role: str | None = None,
        limit: int | None = None,
        include_answers: bool = False,
        validate_curriculum: bool = True,
    ) -> list[dict[str, Any]]:
        """Return deterministic card dictionaries for Qt/API list models.

        The default shape intentionally omits answer prose for a compact
        picker; ``include_answers=True`` returns each full clean-room card.
        Search/filter semantics match :meth:`search_knowledge`.
        """

        cards = self.search_knowledge(
            query,
            kind=kind,
            track=track,
            skill=skill,
            seniority=seniority,
            priority=priority,
            role_id=role_id,
            role=role,
            limit=limit,
            validate_curriculum=validate_curriculum,
        )
        if include_answers:
            return [
                self._knowledge_payload_with_sources(
                    card, validate_curriculum=validate_curriculum
                )
                for card in cards
            ]
        return [self._knowledge_summary(card) for card in cards]

    def knowledge_list(self, **filters: Any) -> list[dict[str, Any]]:
        """Alias for :meth:`knowledge_cards` used by list-oriented clients."""

        return self.knowledge_cards(**filters)

    def list_knowledge(self, **filters: Any) -> list[dict[str, Any]]:
        """Compatibility alias for :meth:`knowledge_cards`."""

        return self.knowledge_cards(**filters)

    def knowledge_card(
        self,
        card_id: str,
        *,
        validate_curriculum: bool = True,
    ) -> KnowledgeCard:
        """Resolve one public card by ID without exposing private Profile data."""

        if not isinstance(card_id, str) or not card_id.strip():
            raise ApplicationError("knowledge card ID must be non-empty text")
        return self.knowledge_catalog(
            validate_curriculum=validate_curriculum
        ).get(card_id)

    # Naming aliases make the facade convenient for CLI, Qt and API clients
    # without creating a second source of truth.
    def knowledge_search(self, query: str | None = None, **filters: Any) -> list[KnowledgeCard]:
        return self.search_knowledge(query, **filters)

    def get_knowledge_card(self, card_id: str, **kwargs: Any) -> KnowledgeCard:
        return self.knowledge_card(card_id, **kwargs)

    def knowledge_card_view(
        self,
        card_id: str,
        *,
        validate_curriculum: bool = True,
    ) -> dict[str, Any]:
        """Return one detached full card mapping for API/UI presentation."""

        card = self.knowledge_card(card_id, validate_curriculum=validate_curriculum)
        return self._knowledge_payload_with_sources(
            card, validate_curriculum=validate_curriculum
        )

    def knowledge_view(self, card_id: str, **kwargs: Any) -> dict[str, Any]:
        """Compatibility alias for :meth:`knowledge_card_view`."""

        return self.knowledge_card_view(card_id, **kwargs)

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

    def set_material_ai_access(
        self, profile_id: str, material_id: str, enabled: bool
    ) -> dict[str, Any]:
        """Change AI access for one explicitly selected material."""

        return set_material_ai_access(
            self.repo_root, profile_id, material_id, enabled
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

    def _problem_environment(self, problem: Problem) -> dict[str, Any]:
        available = self._problem_environment_available(problem)
        return {
            "environment_available": available,
            "environment": "当前可运行" if available else "需要 PyTorch 练习环境",
        }

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
                value["blocked_reason"] = "先完成自助复盘与口述自答。"
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
                role_readiness = self._role_readiness(
                    role, seniority, assessment, state
                )
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
                    **self._problem_environment(self.catalog.get(current.problem_id)),
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
            "due_review_count": len(due_review),
            "due_retention": due_retention[:3],
            "due_retention_count": len(due_retention),
            "unlocks": [
                {
                    "problem_id": problem.id,
                    "title": problem.title,
                    **self._problem_environment(problem),
                }
                for problem in available[:3]
            ],
            "mastered_count": len(state.mastered),
            "role_readiness_metric_version": 2,
            "role_readiness": role_readiness,
        }

    @staticmethod
    def _has_practice_assessment_evidence(
        state: WorkspaceState, problem_id: str
    ) -> bool:
        if state.problem_status(problem_id) in {
            "implemented",
            "reviewed",
            "retained_d2",
            "retained_d7",
            "mastered",
        }:
            return True
        return any(
            attempt.last_public_test is not None
            and attempt.last_public_test.get("status")
            in {"passed", "failed", "timed_out", "import_error"}
            for attempt in state.attempts_for(problem_id)
        )

    def _role_readiness(
        self,
        role: RoleProfile,
        seniority: str,
        assessment: Mapping[str, int],
        state: WorkspaceState,
    ) -> list[dict[str, Any]]:
        """Summarize local evidence without treating missing evidence as failure."""

        domains: dict[str, dict[str, Any]] = {}
        for skill_id, target in role.skill_weights.items():
            skill = self.roles.skills[skill_id]
            assessable = {
                problem_id
                for problem_id in skill.related_problems
                if problem_id in self.catalog.problems
                and self.catalog.get(problem_id).recommendable
            }
            assessed = {
                problem_id
                for problem_id in assessable
                if self._has_practice_assessment_evidence(state, problem_id)
            }
            mastered = assessed.intersection(state.mastered)
            bucket = domains.setdefault(
                skill.domain,
                {
                    "weight": 0.0,
                    "mastery_weight": 0.0,
                    "mastery_sum": 0.0,
                    "coverage_sum": 0.0,
                    "ceiling_sum": 0.0,
                    "self_weight": 0.0,
                    "self_sum": 0.0,
                    "legacy_self_sum": 0.0,
                    "legacy_verified_sum": 0.0,
                    "assessable": set(),
                    "assessed": set(),
                    "mastered": set(),
                },
            )
            bucket["weight"] += target.weight
            bucket["assessable"].update(assessable)
            bucket["assessed"].update(assessed)
            bucket["mastered"].update(mastered)
            target_level = max(1, target.target_level[seniority])
            related = set(skill.related_problems)
            legacy_verified_level = (
                3 * len(related.intersection(state.mastered)) / len(related)
                if related
                else 0.0
            )
            bucket["legacy_self_sum"] += target.weight * min(
                float(assessment.get(skill_id, 0)) / target_level, 1.0
            )
            bucket["legacy_verified_sum"] += target.weight * min(
                legacy_verified_level / target_level, 1.0
            )
            if assessable:
                bucket["ceiling_sum"] += target.weight
                bucket["coverage_sum"] += target.weight * (
                    len(assessed) / len(assessable)
                )
            if assessed:
                bucket["mastery_weight"] += target.weight
                bucket["mastery_sum"] += target.weight * (
                    len(mastered) / len(assessed)
                )
            if skill_id in assessment:
                bucket["self_weight"] += target.weight
                bucket["self_sum"] += target.weight * min(
                    float(assessment[skill_id]) / target_level, 1.0
                )

        result: list[dict[str, Any]] = []
        for domain, value in sorted(domains.items()):
            if value["weight"] <= 0:
                continue
            assessed_mastery = (
                round(value["mastery_sum"] / value["mastery_weight"], 3)
                if value["mastery_weight"]
                else None
            )
            self_attainment = (
                round(value["self_sum"] / value["self_weight"], 3)
                if value["self_weight"]
                else None
            )
            result.append(
                {
                    "id": domain,
                    "label": _DOMAIN_LABELS_ZH.get(
                        domain, domain.replace("_", " ").title()
                    ),
                    "assessed_mastery": assessed_mastery,
                    "assessment_coverage": round(
                        value["coverage_sum"] / value["weight"], 3
                    ),
                    "assessment_coverage_ceiling": round(
                        value["ceiling_sum"] / value["weight"], 3
                    ),
                    "self_assessed_attainment": self_attainment,
                    "self_assessment_coverage": round(
                        value["self_weight"] / value["weight"], 3
                    ),
                    "assessed_problem_count": len(value["assessed"]),
                    "assessable_problem_count": len(value["assessable"]),
                    "mastered_problem_count": len(value["mastered"]),
                    "evidence_scope": "practice",
                    # Compatibility fields for older desktop clients.  New
                    # clients use the explicit evidence and coverage fields.
                    "self_reported": round(
                        value["legacy_self_sum"] / value["weight"], 3
                    ),
                    "verified": round(
                        value["legacy_verified_sum"] / value["weight"], 3
                    ),
                }
            )
        return result

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
            **self._problem_environment(problem),
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
        cards: list[dict[str, Any]] = []
        for problem_id in self.catalog.order:
            problem = self.catalog.problems[problem_id]
            if not tracks.intersection(problem.raw["tracks"]):
                continue
            skills = problem.raw.get("skills", [])
            if not isinstance(skills, list):
                skills = []
            environment = self._problem_environment(problem)
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
                    **environment,
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
        delivery_mode: str = "full_blueprint",
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
            delivery_mode=delivery_mode,
        )

    def personalized_interview_context(
        self,
        profile_id: str,
        *,
        role_id: str,
        seniority: str,
        difficulty: str,
        material_ids: Iterable[str] = (),
        consent_materials: bool = False,
    ):
        """Return the exact context a provider would receive for planning."""

        # Select a small, role-scoped set of reviewed knowledge themes locally.
        # The provider sees prompts/follow-ups only; answer layers remain out
        # of the planning context to keep token use and leakage risk bounded.
        prep = self.interview_prep(
            role_id=role_id,
            seniority=seniority,
            kind="eight_stock",
            limit=6,
            include_answers=False,
        )
        knowledge_cards: list[Mapping[str, Any]] = []
        knowledge = self.knowledge_catalog()
        for summary in prep.get("cards", []):
            if not isinstance(summary, Mapping):
                continue
            card_id = summary.get("id")
            if not isinstance(card_id, str):
                continue
            card = knowledge.cards.get(card_id)
            if card is None:
                continue
            knowledge_cards.append(
                {
                    "id": card.id,
                    "kind": card.kind,
                    "title": card.title,
                    "skills": list(card.skills),
                    "prompt": card.prompt,
                    "follow_ups": list(card.follow_ups),
                }
            )
        return build_role_interview_plan_context_preview(
            self.repo_root,
            profile_id,
            self.roles,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
            material_ids=tuple(material_ids),
            consent_materials=consent_materials,
            knowledge_cards=tuple(knowledge_cards),
        )

    def preview_personalized_interview(
        self,
        profile_id: str,
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
        return preview_personalized_role_interview(
            self.repo_root,
            profile_id,
            self.catalog,
            self.roles,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
            generated_questions=generated_questions,
            plan_context_sha256=plan_context_sha256,
            material_ids=material_ids,
            consent_materials=consent_materials,
            seed=seed,
        )

    def create_personalized_interview(
        self,
        profile_id: str,
        *,
        role_id: str,
        seniority: str,
        difficulty: str,
        generated_questions: Iterable[Mapping[str, Any]],
        plan_context_sha256: str,
        material_ids: Iterable[str] = (),
        consent_materials: bool = False,
        ai_mode: str = "provider",
        seed: int = 0,
    ) -> dict[str, Any]:
        if ai_mode not in {"provider", "codex"}:
            raise ApplicationError("personalized interview AI mode must be provider or codex")
        generated_questions = tuple(generated_questions)
        material_ids = tuple(material_ids)
        context = self.personalized_interview_context(
            profile_id,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
            material_ids=material_ids,
            consent_materials=consent_materials,
        )
        current_context_sha256 = hashlib.sha256(
            context.selected_text.encode("utf-8")
        ).hexdigest()
        if current_context_sha256 != plan_context_sha256:
            raise ApplicationError(
                "面试材料或岗位上下文已变化；请重新生成并确认面试计划"
            )
        # Recompute and validate the same deterministic preview immediately
        # before writing. This makes a stale material SHA or changed coding
        # asset fail rather than silently altering the plan the user approved.
        preview = self.preview_personalized_interview(
            profile_id,
            role_id=role_id,
            seniority=seniority,
            difficulty=difficulty,
            generated_questions=generated_questions,
            plan_context_sha256=plan_context_sha256,
            material_ids=material_ids,
            consent_materials=consent_materials,
            seed=seed,
        )
        session = create_role_interview(
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
            generated_questions=generated_questions,
            plan_context_sha256=plan_context_sha256,
        )
        if [question["source"] for question in session["questions"]] != [
            question["source"] for question in preview["questions"]
        ]:
            raise ApplicationError("personalized interview plan changed before creation")
        return session

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

    def interview_prep(
        self,
        *,
        role_id: str | None = None,
        interview_id: str | None = None,
        profile_id: str = "default",
        seniority: str | None = None,
        query: str | None = None,
        kind: str | None = None,
        skill: str | None = None,
        priority: str | None = None,
        limit: int | None = 20,
        include_answers: bool = False,
    ) -> dict[str, Any]:
        """Return read-only knowledge-card preparation for a role interview.

        This is intentionally an *out-of-session* surface.  A caller can
        scope preparation to a role, or bind it to an existing role interview
        ID to reuse its role/seniority metadata.  Even for an active session,
        this method only reads the frozen session header; it never calls the
        interview clock/current-question resolver and never returns question
        prompts.  Consequently it cannot preview a future question or alter
        the active blueprint/evidence contract.
        """

        if role_id is not None and interview_id is not None:
            raise ApplicationError("choose role_id or interview_id, not both")
        if role_id is None and interview_id is None:
            raise ApplicationError("interview preparation needs a role_id or interview_id")
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise ApplicationError("interview preparation limit must be a positive integer")
        if query is not None and not isinstance(query, str):
            raise ApplicationError("interview preparation query must be text")
        if kind is not None and kind not in {
            "eight_stock",
            "experience_pattern",
            "coding_prompt",
        }:
            raise ApplicationError("unknown knowledge card kind")
        if priority is not None and priority not in {"P0", "P1", "P2", "P3"}:
            raise ApplicationError("knowledge priority must be P0, P1, P2, or P3")

        session_meta: dict[str, Any] | None = None
        if interview_id is not None:
            if not isinstance(interview_id, str) or not interview_id.strip():
                raise ApplicationError("interview_id must be non-empty text")
            # Loading is read-only and validates the profile-local frozen plan.
            # Deliberately do not call current_role_question(): preparation
            # must not consume/reveal active-session timing or future prompts.
            session = load_role_interview(self.repo_root, profile_id, interview_id)
            role_id = session["role_id"]
            session_seniority = session["seniority"]
            if seniority is not None and seniority != session_seniority:
                raise ApplicationError(
                    "seniority does not match the selected role interview"
                )
            seniority = session_seniority
            session_meta = {
                "interview_id": session["interview_id"],
                "profile_id": session["profile_id"],
                "status": session["status"],
                "blueprint_id": session["blueprint_id"],
            }

        assert role_id is not None
        role = self.roles.resolve_role(role_id)
        if seniority is None:
            seniority = "new_grad"
        if seniority not in role.seniority:
            raise ApplicationError(
                f"unsupported seniority for {role.id}: {seniority}"
            )

        # A role's required tracks are a broad eligibility boundary; its
        # weighted skills recover useful cards for roles such as product or
        # evaluation where the current bundle has intentionally sparse track
        # labels.  An explicit --skill is also allowed as a deliberate narrow
        # override, while the result remains bounded to public cards.
        role_tracks = set(role.required_tracks)
        role_skills = set(role.skill_weights)
        catalog = self.knowledge_catalog()
        selected = catalog.select(
            kind=kind,
            skill=skill,
            seniority=seniority,
            priority=priority,
            query=query,
        )
        selected = tuple(
            card
            for card in selected
            if (
                role_tracks.intersection(card.tracks)
                or role_skills.intersection(card.skills)
                or (skill is not None and skill in card.skills)
            )
        )
        if limit is not None:
            selected = selected[:limit]
        if include_answers:
            cards = [
                self._knowledge_payload_with_sources(card)
                for card in selected
            ]
        else:
            cards = [self._knowledge_summary(card) for card in selected]

        blueprint_id = None
        question_types: list[str] = []
        if session_meta is not None:
            blueprint_id = session_meta["blueprint_id"]
        else:
            blueprint_id = role.interview_blueprints.get(seniority)
        if blueprint_id is not None:
            blueprint = self.roles.blueprints.get(blueprint_id)
            if blueprint is not None:
                question_types = list(dict.fromkeys(round_.type for round_ in blueprint.rounds))

        weighted_skills = sorted(
            role.skill_weights.items(),
            key=lambda pair: (-pair[1].weight, pair[0]),
        )
        focus_skills = [
            {
                "id": skill_id,
                "title": self.roles.skills[skill_id].title,
                "weight": target.weight,
            }
            for skill_id, target in weighted_skills
        ]
        return {
            "scope": "interview_prep",
            "role": {
                "id": role.id,
                "title": role.title,
                "seniority": seniority,
                "required_tracks": list(role.required_tracks),
            },
            "blueprint_id": blueprint_id,
            "question_types": question_types,
            "focus_skills": focus_skills,
            "filters": {
                "query": query,
                "kind": kind,
                "skill": skill,
                "priority": priority,
                "limit": limit,
                "include_answers": include_answers,
            },
            "session": session_meta,
            "cards": cards,
        }

    def start_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return start_role_interview(
            self.repo_root, profile_id, interview_id, self.catalog
        )

    def current_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return current_role_question(self.repo_root, profile_id, interview_id)

    def interview_state(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        """Return active or paused question state for desktop recovery UI."""

        return role_interview_state(self.repo_root, profile_id, interview_id)

    def pause_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return pause_role_interview(self.repo_root, profile_id, interview_id)

    def resume_interview(self, profile_id: str, interview_id: str) -> dict[str, Any]:
        return resume_role_interview(self.repo_root, profile_id, interview_id)

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
        """Return the frozen coding answer for the selected interview question.

        A paused interview is intentionally read-only, but its editor still
        needs to render after an application restart.  Use the recovery view
        for that case; all mutation/grader methods continue to use the
        active-only API and therefore remain blocked while paused.
        """

        session = self.interview_session(profile_id, interview_id)
        if session.get("status") == "paused":
            current = self.interview_state(profile_id, interview_id)["question"]
        else:
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
        followup_ids: Iterable[str] = (),
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
            followup_ids=followup_ids,
        )

    def interview_answer_text(
        self, profile_id: str, interview_id: str, question_id: str
    ) -> str:
        try:
            return role_interview_answer_text(
                self.repo_root, profile_id, interview_id, question_id
            )
        except RoleInterviewError as error:
            raise ApplicationError(str(error)) from error

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
        """Return the newest *answerable* active/paused interview.

        An active session whose local deadline has elapsed is deliberately not
        returned as resumable: the learner must finish it as incomplete, not
        be sent back into a dead "continue" action.  ``preferred_interview``
        still exposes that expired session for its explicit finish path.
        """

        active = []
        for session in list_role_interviews(self.repo_root, profile_id):
            if session["status"] == "paused":
                active.append(session)
                continue
            if session["status"] != "active":
                continue
            try:
                role_interview_state(
                    self.repo_root, profile_id, session["interview_id"]
                )
            except RoleInterviewError:
                # Expired (or otherwise no-longer-answerable) sessions are
                # recovered through the presentation view below.
                continue
            active.append(session)
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
            evidence_view = {
                "question_id": question_id,
                "title": question["title"],
                "source": assessment["source"],
                "evidence": assessment["evidence"],
                "confidence": assessment["confidence"],
                "score": result["question_scores"].get(question_id),
            }
            linked_followups = assessment.get("followup_ids", [])
            if linked_followups:
                evidence_view["followup_ids"] = list(linked_followups)
            assessment_evidence.append(evidence_view)
        question_titles = {
            question["question_id"]: question["title"]
            for question in session["questions"]
        }
        followups = [
            {
                key: followup[key]
                for key in (
                    "followup_id",
                    "parent_question_id",
                    "prompt",
                    "answer",
                    "source",
                    "recorded_at",
                )
            }
            | {
                "parent_title": question_titles.get(
                    followup["parent_question_id"], followup["parent_question_id"]
                )
            }
            for followup in session.get("followups", [])
            if isinstance(followup, Mapping)
        ]
        view = {
            "interview_id": interview_id,
            "status": session["status"],
            "role_id": session["role_id"],
            "seniority": session["seniority"],
            "difficulty": session["difficulty"],
            "completion_status": result["completion_status"],
            "overall_score": result["overall_score"],
            "question_scores": dict(result["question_scores"]),
            "assessment_evidence": assessment_evidence,
            "followups": followups,
            "skill_scores": dict(result["skill_scores"]),
            "critical_gaps": list(result["critical_gaps"]),
            "unanswered": list(result["unanswered"]),
            "unscored": list(result["unscored"]),
            "summary": result["summary"],
            "finished_at": result["finished_at"],
        }
        if session.get("delivery_mode") == "non_coding_fallback":
            view["delivery_mode"] = "non_coding_fallback"
            view["blueprint_coverage"] = dict(session["blueprint_coverage"])
        return view

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
        # Keep an expired active session reachable so the desktop can show a
        # truthful "timed out → finish incomplete" action after restart.
        sessions = list_role_interviews(self.repo_root, profile_id)
        for session in reversed(sessions):
            if session.get("status") != "active":
                continue
            try:
                role_interview_state(
                    self.repo_root, profile_id, session["interview_id"]
                )
            except RoleInterviewError:
                return {"kind": "expired", "interview_id": session["interview_id"]}
        result = self.recent_interview_result(profile_id)
        if result is not None:
            return {"kind": "result", **result}
        return None
