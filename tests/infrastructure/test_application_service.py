from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.events import append_event
from llm_interview_lab.workspace import event_schema_path, load_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='application-fixture'\nversion='0'\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n", encoding="utf-8"
    )
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _mark_implemented(
    service: ApplicationService, profile_id: str, problem_id: str
) -> tuple[str, str]:
    service.start_practice(profile_id, problem_id)
    current = service.current_submission(profile_id)
    assert current is not None
    paths = profile_paths(service.repo_root, profile_id)
    append_event(
        paths.events_file,
        event_schema_path(service.repo_root),
        profile_id=profile_id,
        event_type="task_implemented",
        problem_id=problem_id,
        attempt_id=current["attempt_id"],
        payload={"submission_sha256": current["sha256"]},
        timestamp=T0,
    )
    return current["attempt_id"], current["sha256"]


def _mark_reviewed(
    service: ApplicationService,
    profile_id: str,
    problem_id: str,
    *,
    timestamp: datetime = T0,
) -> None:
    attempt_id, sha256 = _mark_implemented(service, profile_id, problem_id)
    paths = profile_paths(service.repo_root, profile_id)
    append_event(
        paths.events_file,
        event_schema_path(service.repo_root),
        profile_id=profile_id,
        event_type="review_completed",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={
            "submission_sha256": sha256,
            "contract_status": "passed",
            "oral_status": "passed",
            "code_explanation": "Synthetic contract explanation.",
            "complexity": "O(n) time and O(1) auxiliary space.",
            "boundary_conditions": "Empty and invalid inputs are explicit.",
        },
        timestamp=timestamp,
    )


def test_shared_application_service_initializes_role_and_local_material(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    cards = service.role_cards()
    assert len(cards) == 8
    assert all(6 <= len(card["top_skills"]) <= 8 for card in cards)
    result = service.initialize_profile(
        "learner-one",
        role_id="applied_ai_engineer",
        seniority="new_grad",
        ai_mode="disabled",
    )
    assert result["created"]
    profile = load_profile(profile_paths(root, "learner-one"), root)
    assert profile["role_preferences"]["primary_role"] == "applied_ai_engineer"
    dashboard = service.dashboard("learner-one")
    assert dashboard["unlocks"]
    assert dashboard["role"]["title"] == "Applied AI Engineer"

    source = tmp_path / "resume.md"
    source.write_text("Synthetic resume. No employer data.\n", encoding="utf-8")
    material = service.add_career_material(
        "learner-one",
        source,
        kind="resume",
        title="Synthetic resume",
        ai_access=True,
    )
    assert material["id"].startswith("material-")
    assert service.material_cards("learner-one") == [material]
    assert "No employer data" not in (
        root / "workspace/profiles/learner-one/materials/manifest.json"
    ).read_text(encoding="utf-8")


def test_every_role_has_a_runnable_first_unlock_without_torch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    monkeypatch.setattr(
        "llm_interview_lab.application.importlib.util.find_spec",
        lambda _: None,
    )

    for index, role in enumerate(service.role_cards(), start=1):
        profile_id = f"role-user-{index}"
        service.initialize_profile(
            profile_id,
            role_id=role["id"],
            seniority="new_grad",
            ai_mode="disabled",
        )
        unlocks = service.dashboard(profile_id)["unlocks"]

        assert unlocks, role["id"]
        assert unlocks[0]["environment_available"] is True, (role["id"], unlocks)
        service.start_practice(profile_id, unlocks[0]["problem_id"])
        current = service.current_submission(profile_id)
        assert current is not None
        assert current["problem_id"] == unlocks[0]["problem_id"]


def test_knowledge_search_role_uses_weighted_skills_as_fallback(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)

    # The algorithm role's broad eligibility tracks intentionally do not
    # include ``vlm_algorithm``.  Its weighted VLM skill should still surface
    # the research-backed card, and the public alias must resolve identically.
    by_id = service.knowledge_cards(
        role_id="ai_algorithm_research_engineer",
        query="动态分辨率",
        limit=20,
    )
    by_alias = service.knowledge_cards(
        role="VLM Algorithm Engineer",
        query="动态分辨率",
        limit=20,
    )
    assert any(card["id"] == "EGT-VLM-005" for card in by_id)
    assert any(card["id"] == "EGT-VLM-005" for card in by_alias)

    # An explicit skill is a deliberate narrow override, even when it is not
    # part of the role's weighted defaults.
    explicit = service.knowledge_cards(
        role_id="ai_algorithm_research_engineer",
        skill="skill.llm_vlm.multimodal_data",
        limit=20,
    )
    assert any(card["id"] == "COD-VLM-003" for card in explicit)


def test_noninteractive_quickstart_is_one_command_and_needs_no_ai(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "llm_interview_lab.cli",
            "quickstart",
            "--profile",
            "first-user",
            "--role",
            "ai_product_manager",
            "--seniority",
            "new_grad",
            "--ai",
            "disabled",
            "--non-interactive",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PROFILE first-user: created" in completed.stdout
    assert "ROLE AI Product Manager" in completed.stdout
    assert "AI disabled" in completed.stdout
    assert "NEXT llm-lab test" in completed.stdout
    assert profile_paths(root, "first-user").profile_file.is_file()


def test_application_service_edits_only_the_active_interview_coding_answer(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile(
        "coding-user", role_id="applied_ai_engineer", seniority="new_grad"
    )
    session = service.create_interview(
        "coding-user",
        role_id="applied_ai_engineer",
        seniority="new_grad",
        difficulty="medium",
        seed=3,
    )
    interview_id = session["interview_id"]
    service.start_interview("coding-user", interview_id)
    current = service.current_interview("coding-user", interview_id)["question"]
    assert current is not None and current["kind"] == "coding"
    original = service.current_interview_coding_submission(
        "coding-user", interview_id
    )
    replacement = original["text"] + "\n# local timed attempt\n"
    saved = service.save_interview_coding_submission(
        "coding-user", interview_id, replacement
    )
    assert saved["text"] == replacement
    assert saved["sha256"] != original["sha256"]
    assert service.current_interview_coding_submission(
        "coding-user", interview_id
    )["text"] == replacement


def test_dashboard_only_exposes_due_verified_retention_with_direct_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("learner-one", role_id="applied_ai_engineer")
    _mark_reviewed(service, "learner-one", "FND-001", timestamp=T0)

    state_calls = 0
    original_state = service._state

    def counted_state(profile_id: str):
        nonlocal state_calls
        state_calls += 1
        return original_state(profile_id)

    monkeypatch.setattr(service, "_state", counted_state)

    assert service.dashboard(
        "learner-one", now=T0 + timedelta(days=1)
    )["due_retention"] == []
    assert state_calls == 1
    state_calls = 0
    due = service.dashboard(
        "learner-one", now=T0 + timedelta(days=2)
    )["due_retention"]
    assert state_calls == 1
    assert due == [
        {
            "problem_id": "FND-001",
            "title": "Wrong Prediction Count",
            "stage": "d2",
            "due_at": (T0 + timedelta(days=2)).isoformat(),
            "actionable": True,
            "blocked_reason": "",
        }
    ]
    started = service.start_retention(
        "learner-one", "FND-001", "d2", now=T0 + timedelta(days=2)
    )
    assert started["retention_stage"] == "d2"
    resumed = service.dashboard(
        "learner-one", now=T0 + timedelta(days=3)
    )["due_retention"]
    assert resumed[0]["problem_id"] == "FND-001"
    assert resumed[0]["actionable"] is True


def test_practice_actions_distinguish_review_future_environment_and_due(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("learner-one", role_id="applied_ai_engineer")
    _mark_implemented(service, "learner-one", "FND-001")
    before_review = service.practice_actions("learner-one", "FND-001", now=T0)
    assert before_review["review"]["state"] == "review_available"

    paths = profile_paths(root, "learner-one")
    current = service.current_submission("learner-one")
    assert current is not None
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id="learner-one",
        event_type="review_completed",
        problem_id="FND-001",
        attempt_id=current["attempt_id"],
        payload={
            "submission_sha256": current["sha256"],
            "contract_status": "passed",
            "oral_status": "passed",
            "code_explanation": "Synthetic contract explanation.",
            "complexity": "O(n).",
            "boundary_conditions": "Empty input is rejected.",
        },
        timestamp=T0,
    )
    future = service.practice_actions(
        "learner-one", "FND-001", now=T0 + timedelta(days=1)
    )
    assert future["retention"]["d2"]["state"] == "future"
    due = service.practice_actions(
        "learner-one", "FND-001", now=T0 + timedelta(days=2)
    )
    assert due["retention"]["d2"]["state"] == "due"

    with monkeypatch.context() as patch:
        patch.setattr(
            type(service.catalog.get("FND-001")),
            "retention_variant",
            lambda self, repo_root, stage: None,
        )
        missing_asset = service.practice_actions(
            "learner-one", "FND-001", now=T0 + timedelta(days=2)
        )
        assert missing_asset["retention"]["d2"]["state"] == "missing_asset"
        assert service.dashboard(
            "learner-one", now=T0 + timedelta(days=2)
        )["due_retention"] == []

    monkeypatch.setattr(service, "_problem_environment_available", lambda problem: False)
    missing_environment = service.practice_actions(
        "learner-one", "FND-001", now=T0 + timedelta(days=2)
    )
    assert missing_environment["retention"]["d2"]["state"] == "missing_environment"


def test_interview_configuration_and_canonical_result_preference(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("learner-one", role_id="ai_product_manager")

    medium = service.interview_configuration(
        "ai_product_manager", "new_grad", "medium"
    )
    hard = service.interview_configuration(
        "ai_product_manager", "new_grad", "hard"
    )
    assert medium["available"] is True
    assert hard["available"] is False
    assert hard["missing_rounds"]

    finished = service.create_interview(
        "learner-one",
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="medium",
    )
    service.start_interview("learner-one", finished["interview_id"])
    first = service.current_interview(
        "learner-one", finished["interview_id"]
    )["question"]
    assert first is not None
    answer = "I separate assumptions from evidence and define a measurable outcome."
    service.answer_interview(
        "learner-one", finished["interview_id"], first["question_id"], answer
    )
    service.score_interview(
        "learner-one",
        finished["interview_id"],
        first["question_id"],
        {name: 3 for name in first["rubric"]["dimensions"]},
        evidence="The answer explicitly separates assumptions from evidence.",
        source="human",
        confidence="high",
    )
    service.finish_interview(
        "learner-one", finished["interview_id"], confirm_incomplete=True
    )
    preferred = service.preferred_interview("learner-one")
    assert preferred is not None
    assert preferred["kind"] == "result"
    assert preferred["completion_status"] == "incomplete"
    assert preferred["overall_score"] > 0
    assert preferred["unscored"] == []
    assert preferred["assessment_evidence"] == [
        {
            "question_id": first["question_id"],
            "title": first["title"],
            "source": "human",
            "evidence": "The answer explicitly separates assumptions from evidence.",
            "confidence": "high",
            "score": preferred["question_scores"][first["question_id"]],
        }
    ]

    active = service.create_interview(
        "learner-one",
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="medium",
        seed=1,
    )
    service.start_interview("learner-one", active["interview_id"])
    preferred = service.preferred_interview("learner-one")
    assert preferred == {"kind": "active", "interview_id": active["interview_id"]}


def test_problem_environment_is_visible_before_home_or_exercise_navigation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("environment-user")
    monkeypatch.setattr(service, "_problem_environment_available", lambda problem: False)

    view = service.problem_view("LOSS-014")
    assert view["environment_available"] is False
    assert view["environment"] == "需要 PyTorch 练习环境"

    dashboard = service.dashboard("environment-user")
    assert dashboard["unlocks"]
    assert dashboard["unlocks"][0]["environment_available"] is False
    service.start_practice("environment-user", dashboard["unlocks"][0]["problem_id"])
    current = service.dashboard("environment-user")["current"]
    assert current["environment_available"] is False


def test_interview_prep_is_read_only_and_does_not_preview_active_questions(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile(
        "prep-user", role_id="ai_product_manager", seniority="new_grad"
    )
    session = service.create_interview(
        "prep-user",
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="medium",
    )
    interview_id = session["interview_id"]
    service.start_interview("prep-user", interview_id)
    session_path = (
        root / "workspace" / "profiles" / "prep-user" / "interviews"
        / interview_id / "session.json"
    )
    before = hashlib.sha256(session_path.read_bytes()).hexdigest()

    prep = service.interview_prep(
        interview_id=interview_id,
        profile_id="prep-user",
        kind="eight_stock",
        limit=3,
    )
    after = hashlib.sha256(session_path.read_bytes()).hexdigest()
    assert before == after
    assert prep["scope"] == "interview_prep"
    assert prep["session"]["status"] == "active"
    assert prep["question_types"] == [
        "product_case",
        "evaluation_case",
        "behavioral",
    ]
    assert prep["cards"]
    assert all("prompt" not in card for card in prep["cards"])

    # The normal active-session resolver remains the sole source of the
    # current question and still exposes exactly one question at a time.
    current = service.current_interview("prep-user", interview_id)
    assert current["question"]["question_id"] == "q-001"
    assert current["question"]["prompt"]
