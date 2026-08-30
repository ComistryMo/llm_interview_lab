from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.ai.context_builder import (
    ContextBuilderError,
    build_role_interview_context_preview,
)
from llm_interview_lab.catalog import load_catalog
from llm_interview_lab.application import ApplicationService
from llm_interview_lab.context import build_interview_context, serialize_context
from llm_interview_lab.materials import add_material, resolve_material_path
from llm_interview_lab.role_interviews import (
    RoleInterviewError,
    create_role_interview,
    current_role_question,
    finish_role_interview,
    interview_preflight,
    load_role_interview,
    record_role_answer,
    record_role_assessment,
    record_role_followup,
    role_interview_report,
    start_role_interview,
    pause_role_interview,
    resume_role_interview,
    role_interview_state,
)
from llm_interview_lab.roles import load_role_catalog
from llm_interview_lab.workspace import init_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
T0 = datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc)


def _repository(tmp_path: Path, *profiles: str) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='role-interview-fixture'\nversion='0'\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n", encoding="utf-8"
    )
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    shutil.copytree(REPO_ROOT / "coach", root / "coach")
    shutil.copy2(REPO_ROOT / "AGENTS.md", root / "AGENTS.md")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    for profile in profiles or ("learner-one",):
        init_profile(root, profile)
    return root


def _catalogs(root: Path):
    catalog = load_catalog(root)
    return catalog, load_role_catalog(root, curriculum=catalog)


def _answer_and_score_all(root: Path, interview_id: str, *, profile: str = "learner-one") -> None:
    while True:
        current = current_role_question(root, profile, interview_id, now=T0 + timedelta(minutes=1))
        question = current["question"]
        if question is None:
            return
        assert question["kind"] != "coding"
        record_role_answer(
            root,
            profile,
            interview_id,
            question["question_id"],
            "I separate known facts from assumptions, define measurable evidence, and compare trade-offs.",
            now=T0 + timedelta(minutes=2),
        )
        record_role_assessment(
            root,
            profile,
            interview_id,
            question["question_id"],
            {name: 3 for name in question["rubric"]["dimensions"]},
            evidence=f"{question['question_id']} states assumptions and measurable evidence.",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=3),
        )


def test_product_role_interview_runs_one_question_at_a_time_and_reports_evidence(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="medium",
        seed=7,
        now=T0,
    )
    assert session["status"] == "ready"
    assert [question["kind"] for question in session["questions"]] == [
        "product_case",
        "evaluation_case",
        "behavioral",
    ]
    assert all(question["source"]["kind"] == "fixed_item" for question in session["questions"])

    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    first = current_role_question(root, "learner-one", session["interview_id"], now=T0)
    assert first["question"]["question_id"] == "q-001"
    assert first["remaining_seconds"] == 75 * 60
    record_role_answer(
        root,
        "learner-one",
        session["interview_id"],
        "q-001",
        "A bounded answer with explicit assumptions and evidence.",
        now=T0 + timedelta(minutes=1),
    )
    record_role_followup(
        root,
        "learner-one",
        session["interview_id"],
        parent_question_id="q-001",
        prompt="Which assumption would you test first?",
        answer="The riskiest user-value assumption, with a reversible pilot.",
        source="ai",
        now=T0 + timedelta(minutes=2),
    )
    first_question = session["questions"][0]
    record_role_assessment(
        root,
        "learner-one",
        session["interview_id"],
        "q-001",
        {name: 3 for name in first_question["rubric"]["dimensions"]},
        evidence="q-001 distinguishes assumptions and proposes a reversible pilot.",
        source="ai",
        confidence="medium",
        now=T0 + timedelta(minutes=3),
    )
    with pytest.raises(RoleInterviewError, match="already has recorded assessment"):
        record_role_assessment(
            root,
            "learner-one",
            session["interview_id"],
            "q-001",
            {name: 5 for name in first_question["rubric"]["dimensions"]},
            evidence="A second scorer must not overwrite the first canonical assessment.",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=3),
        )
    assert current_role_question(
        root, "learner-one", session["interview_id"], now=T0 + timedelta(minutes=4)
    )["question"]["question_id"] == "q-002"

    # Complete the remaining primary questions; the first assessment remains intact.
    while True:
        current = current_role_question(
            root, "learner-one", session["interview_id"], now=T0 + timedelta(minutes=5)
        )["question"]
        if current is None:
            break
        record_role_answer(
            root,
            "learner-one",
            session["interview_id"],
            current["question_id"],
            "I define success, risks, evidence, owners, and explicit uncertainty.",
            now=T0 + timedelta(minutes=6),
        )
        record_role_assessment(
            root,
            "learner-one",
            session["interview_id"],
            current["question_id"],
            {name: 5 for name in current["rubric"]["dimensions"]},
            evidence=f"{current['question_id']} contains concrete success and risk evidence.",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=7),
        )
    finished = finish_role_interview(
        root,
        "learner-one",
        session["interview_id"],
        summary="Strong framing; deepen failure-mode quantification.",
        now=T0 + timedelta(minutes=20),
    )
    assert finished["result"]["completion_status"] == "completed"
    assert 0 < finished["result"]["overall_score"] <= 100
    assert finished["result"]["skill_scores"]
    with pytest.raises(RoleInterviewError, match="active interview"):
        record_role_assessment(
            root,
            "learner-one",
            session["interview_id"],
            "q-001",
            {name: 5 for name in first_question["rubric"]["dimensions"]},
            evidence="A late assessment must not rewrite frozen result evidence.",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=21),
        )
    with pytest.raises(RoleInterviewError, match="active interview"):
        record_role_followup(
            root,
            "learner-one",
            session["interview_id"],
            parent_question_id="q-001",
            prompt="Late follow-up?",
            answer="This must not be recorded after finish.",
            source="human",
            now=T0 + timedelta(minutes=21),
        )
    report = role_interview_report(root, "learner-one", session["interview_id"])
    assert "Practice mastery: **unchanged**" in report
    assert "offer probability" in report


def test_role_blueprint_selects_validated_coding_problem_and_creates_local_starter(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    # Keep the contract covered on the default (no optional torch) CI job;
    # retain the original PyTorch-heavy role when that extra is installed.
    role_id = (
        "ai_algorithm_research_engineer"
        if importlib.util.find_spec("torch") is not None
        else "applied_ai_engineer"
    )
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id=role_id,
        seniority="intern",
        difficulty="medium",
        now=T0,
    )
    coding = session["questions"][0]
    assert coding["kind"] == "coding"
    assert catalog.get(coding["source"]["id"]).recommendable
    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    submission = (
        profile_paths(root, "learner-one").interviews_root
        / session["interview_id"]
        / "coding"
        / "q-001"
        / "submission.py"
    )
    assert submission.is_file()
    assert "NotImplementedError" in submission.read_text(encoding="utf-8") or "TODO" in submission.read_text(encoding="utf-8")


def test_grader_source_is_restricted_to_coding_rounds(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="medium",
        now=T0,
    )
    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    question = current_role_question(
        root, "learner-one", session["interview_id"], now=T0
    )["question"]
    assert question["kind"] != "coding"
    record_role_answer(
        root,
        "learner-one",
        session["interview_id"],
        question["question_id"],
        "A bounded answer with explicit assumptions and evidence.",
        now=T0,
    )
    with pytest.raises(RoleInterviewError, match="only valid for coding"):
        record_role_assessment(
            root,
            "learner-one",
            session["interview_id"],
            question["question_id"],
            {name: 3 for name in question["rubric"]["dimensions"]},
            evidence="A fake grader result must never score a text answer.",
            source="grader",
            confidence="high",
            now=T0,
        )


def test_coding_assessment_is_grader_bound_and_rejects_stale_or_subjective_scores(
    tmp_path: Path,
) -> None:
    """A coding round cannot be upgraded by an arbitrary human/AI score."""

    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="applied_ai_engineer",
        seniority="intern",
        difficulty="medium",
        now=T0,
    )
    interview_id = session["interview_id"]
    start_role_interview(root, "learner-one", interview_id, catalog, now=T0)
    question = current_role_question(root, "learner-one", interview_id, now=T0)["question"]
    assert question is not None and question["kind"] == "coding"
    submission = (
        profile_paths(root, "learner-one").interviews_root
        / interview_id
        / "coding"
        / question["question_id"]
        / "submission.py"
    )
    digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    path = profile_paths(root, "learner-one").interviews_root / interview_id / "session.json"
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["coding_evidence"][question["question_id"]] = {
        "submission_sha256": digest,
        "status": "failed",
        "passed": 0,
        "failed": 1,
        "duration_ms": 12,
        "recorded_at": "2026-08-28T09:01:00Z",
    }
    path.write_text(json.dumps(stored), encoding="utf-8")
    dimensions = {name: 5 for name in question["rubric"]["dimensions"]}
    with pytest.raises(RoleInterviewError, match="local Grader"):
        record_role_assessment(
            root,
            "learner-one",
            interview_id,
            question["question_id"],
            dimensions,
            evidence="human says this is excellent",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=1),
        )
    with pytest.raises(RoleInterviewError, match="5=passed, 1=failed"):
        record_role_assessment(
            root,
            "learner-one",
            interview_id,
            question["question_id"],
            dimensions,
            evidence="fake grader evidence",
            source="grader",
            confidence="high",
            now=T0 + timedelta(minutes=1),
        )
    recorded = record_role_assessment(
        root,
        "learner-one",
        interview_id,
        question["question_id"],
        {name: 1 for name in question["rubric"]["dimensions"]},
        evidence="caller text is ignored for objective evidence",
        source="grader",
        confidence="high",
        now=T0 + timedelta(minutes=1),
    )
    assessment = recorded["assessments"][question["question_id"]]
    assert assessment["source"] == "grader"
    assert "submission_sha256=" + digest in assessment["evidence"]

    # A later edit invalidates the same persisted Grader result.
    session_two = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="applied_ai_engineer",
        seniority="intern",
        difficulty="medium",
        seed=1,
        now=T0,
    )
    start_role_interview(root, "learner-one", session_two["interview_id"], catalog, now=T0)
    second_question = current_role_question(
        root, "learner-one", session_two["interview_id"], now=T0
    )["question"]
    assert second_question is not None and second_question["kind"] == "coding"
    second_submission = (
        profile_paths(root, "learner-one").interviews_root
        / session_two["interview_id"]
        / "coding"
        / second_question["question_id"]
        / "submission.py"
    )
    second_digest = hashlib.sha256(second_submission.read_bytes()).hexdigest()
    second_path = (
        profile_paths(root, "learner-one").interviews_root
        / session_two["interview_id"]
        / "session.json"
    )
    second_stored = json.loads(second_path.read_text(encoding="utf-8"))
    second_stored["coding_evidence"][second_question["question_id"]] = {
        "submission_sha256": second_digest,
        "status": "passed",
        "passed": 1,
        "failed": 0,
        "duration_ms": 12,
        "recorded_at": "2026-08-28T09:01:00Z",
    }
    second_path.write_text(json.dumps(second_stored), encoding="utf-8")
    second_submission.write_text(
        second_submission.read_text(encoding="utf-8") + "\n# changed\n",
        encoding="utf-8",
    )
    with pytest.raises(RoleInterviewError, match="changed after Grader"):
        record_role_assessment(
            root,
            "learner-one",
            session_two["interview_id"],
            second_question["question_id"],
            {name: 5 for name in second_question["rubric"]["dimensions"]},
            evidence="stale",
            source="grader",
            confidence="high",
            now=T0 + timedelta(minutes=1),
        )


def test_interview_preflight_is_strict_and_writes_nothing_when_unavailable(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)

    available = interview_preflight(
        root,
        catalog,
        roles,
        role_id="applied_ai_engineer",
        seniority="new_grad",
        difficulty="medium",
    )
    assert available["available"] is True
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="applied_ai_engineer",
        seniority="new_grad",
        difficulty="medium",
        now=T0,
    )
    coding = session["questions"][0]
    assert coding["skills"] == ["skill.agent_application.tool_calling"]
    blueprint = roles.blueprints[session["blueprint_id"]]
    for question in session["questions"]:
        round_skills = set(blueprint.rounds[question["round_index"]].skills)
        assert question["skills"]
        assert set(question["skills"]).issubset(round_skills)
        if question["source"]["kind"] == "fixed_item":
            assert set(question["skills"]).issubset(
                roles.items[question["source"]["id"]].skills
            )

    interviews_root = profile_paths(root, "learner-one").interviews_root
    before = sorted(path.name for path in interviews_root.iterdir())
    unavailable = interview_preflight(
        root,
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        difficulty="hard",
    )
    assert unavailable["available"] is False
    assert unavailable["missing_rounds"]
    with pytest.raises(RoleInterviewError, match="缺少满足岗位"):
        create_role_interview(
            root,
            "learner-one",
            catalog,
            roles,
            role_id="ai_product_manager",
            seniority="new_grad",
            difficulty="hard",
            now=T0,
        )
    assert sorted(path.name for path in interviews_root.iterdir()) == before


def test_interview_preflight_reports_missing_torch_without_relaxing_skills(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    result = interview_preflight(
        root,
        catalog,
        roles,
        role_id="ai_algorithm_research_engineer",
        seniority="intern",
        difficulty="medium",
        torch_available=False,
    )
    assert result["available"] is False
    assert result["missing_environment"] == ["pytorch"]
    coding = next(item for item in result["missing_rounds"] if item["type"] == "coding")
    assert coding["reason"] == "missing_environment"


def test_interview_coding_skills_use_only_ontology_reverse_index(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    skill_id = "skill.agent_application.tool_calling"
    skills = dict(roles.skills)
    skills[skill_id] = replace(
        skills[skill_id],
        related_problems=tuple(
            problem_id
            for problem_id in skills[skill_id].related_problems
            if problem_id != "AGT-006"
        ),
    )
    roles_without_reverse_link = replace(roles, skills=skills)
    problems = dict(catalog.problems)
    problem = problems["AGT-006"]
    problems[problem.id] = replace(
        problem,
        raw={**problem.raw, "canonical_skills": [skill_id]},
    )
    catalog_with_legacy_hint = replace(catalog, problems=problems)

    result = interview_preflight(
        root,
        catalog_with_legacy_hint,
        roles_without_reverse_link,
        role_id="applied_ai_engineer",
        seniority="new_grad",
        difficulty="medium",
    )
    coding = next(item for item in result["missing_rounds"] if item["type"] == "coding")
    assert coding["candidate_ids"] == []
    assert result["available"] is False


@pytest.mark.parametrize(
    ("problem_id", "skill_ids"),
    [
        ("FND-004", {"skill.python_engineering.data_contracts", "skill.data_mlops.data_quality"}),
        ("TNS-011", {"skill.deep_learning.tensor_ops"}),
        (
            "CAP-LOSS-001",
            {
                "skill.deep_learning.tensor_ops",
                "skill.deep_learning.autograd",
                "skill.deep_learning.neural_layers",
                "skill.deep_learning.losses",
            },
        ),
        (
            "CAP-TRN-001",
            {
                "skill.data_mlops.reproducibility",
                "skill.deep_learning.tensor_ops",
                "skill.deep_learning.autograd",
                "skill.deep_learning.neural_layers",
                "skill.deep_learning.losses",
                "skill.deep_learning.optimizers",
            },
        ),
        ("AGT-006", {"skill.agent_application.tool_calling"}),
    ],
)
def test_skill_ontology_reverse_index_covers_authored_problems(
    tmp_path: Path, problem_id: str, skill_ids: set[str]
) -> None:
    root = _repository(tmp_path)
    _, roles = _catalogs(root)
    actual = {
        skill.id for skill in roles.skills.values() if problem_id in skill.related_problems
    }
    assert skill_ids.issubset(actual)


def test_skill_ontology_does_not_overstate_logprob_or_toy_trainer_evidence(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    _, roles = _catalogs(root)
    assert "PT-002" not in roles.skills[
        "skill.post_training_rl.policy_optimization"
    ].related_problems
    assert "CAP-TRN-001" not in roles.skills[
        "skill.data_mlops.pipelines"
    ].related_problems


def test_every_role_has_a_truthful_default_new_grad_interview(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    unavailable = {}
    for role_id in roles.roles:
        value = interview_preflight(
            root,
            catalog,
            roles,
            role_id=role_id,
            seniority="new_grad",
            difficulty="medium",
            torch_available=True,
        )
        if not value["available"]:
            unavailable[role_id] = value["missing_rounds"]
    assert unavailable == {}


def test_every_ready_interview_item_is_reachable_from_a_blueprint(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    reachable: set[str] = set()
    for role_id, role in roles.roles.items():
        for seniority in role.seniority:
            for difficulty in ("easy", "medium", "hard"):
                value = interview_preflight(
                    root,
                    catalog,
                    roles,
                    role_id=role_id,
                    seniority=seniority,
                    difficulty=difficulty,
                    torch_available=True,
                )
                for round_value in value.get("rounds", []):
                    reachable.update(round_value["candidate_ids"])
    ready_items = {item.id for item in roles.items.values() if item.status == "ready"}
    assert ready_items.issubset(reachable)


def test_timer_incomplete_finish_and_profile_isolation(tmp_path: Path) -> None:
    root = _repository(tmp_path, "learner-one", "learner-two")
    catalog, roles = _catalogs(root)
    one = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="intern",
        now=T0,
    )
    start_role_interview(root, "learner-one", one["interview_id"], catalog, now=T0)
    with pytest.raises(RoleInterviewError, match="expired"):
        current_role_question(
            root, "learner-one", one["interview_id"], now=T0 + timedelta(hours=2)
        )
    finished = finish_role_interview(
        root,
        "learner-one",
        one["interview_id"],
        now=T0 + timedelta(hours=2),
    )
    assert finished["result"]["completion_status"] == "incomplete"
    assert finished["result"]["overall_score"] == 0
    assert finished["result"]["unanswered"] == [
        question["question_id"] for question in finished["questions"]
    ]
    assert finished["result"]["unscored"] == []
    with pytest.raises(RoleInterviewError, match="does not exist"):
        load_role_interview(root, "learner-two", one["interview_id"])


def test_expired_active_interview_is_not_presented_as_resumable(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    created = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="intern",
        now=T0,
    )
    start_role_interview(root, "learner-one", created["interview_id"], catalog, now=T0)
    service = ApplicationService(root)
    assert service.resumable_interview("learner-one") is None
    preferred = service.preferred_interview("learner-one")
    assert preferred == {"kind": "expired", "interview_id": created["interview_id"]}


def test_pause_resume_persists_clock_and_blocks_mutations(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    created = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="intern",
        now=T0,
    )
    interview_id = created["interview_id"]
    start_role_interview(root, "learner-one", interview_id, catalog, now=T0)

    paused = pause_role_interview(
        root, "learner-one", interview_id, now=T0 + timedelta(minutes=7)
    )
    assert paused["status"] == "paused"
    assert paused["deadline"] is None
    assert paused["paused_at"] == "2026-08-28T09:07:00Z"
    expected_remaining = created["duration_minutes"] * 60 - 7 * 60
    assert paused["paused_remaining_seconds"] == expected_remaining
    assert [item["event"] for item in paused["timeline"]][-1] == "paused"
    assert role_interview_state(root, "learner-one", interview_id)["status"] == "paused"
    with pytest.raises(RoleInterviewError, match="not active"):
        current_role_question(root, "learner-one", interview_id, now=T0 + timedelta(minutes=8))
    with pytest.raises(RoleInterviewError, match="not active"):
        record_role_answer(
            root, "learner-one", interview_id, "q-001", "must be blocked", now=T0
        )
    with pytest.raises(RoleInterviewError, match="explicit incomplete"):
        finish_role_interview(root, "learner-one", interview_id, now=T0 + timedelta(minutes=8))

    resumed = resume_role_interview(
        root, "learner-one", interview_id, now=T0 + timedelta(hours=1)
    )
    assert resumed["status"] == "active"
    assert resumed["paused_at"] is None
    assert resumed["paused_remaining_seconds"] is None
    assert resumed["deadline"] == (
        T0 + timedelta(hours=1, seconds=expected_remaining)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert [item["event"] for item in resumed["timeline"]][-1] == "resumed"
    state = role_interview_state(root, "learner-one", interview_id, now=T0 + timedelta(hours=1))
    assert state["status"] == "active"
    assert state["remaining_seconds"] == expected_remaining

    service = ApplicationService(root)
    wrapper_session = service.create_interview(
        "learner-one", role_id="ai_product_manager", seniority="intern"
    )
    service.start_interview("learner-one", wrapper_session["interview_id"])
    pause_again = service.pause_interview("learner-one", wrapper_session["interview_id"])
    assert pause_again["status"] == "paused"
    resumed_again = service.resume_interview("learner-one", wrapper_session["interview_id"])
    assert resumed_again["status"] == "active"


def test_paused_session_is_resumable_and_old_shape_is_readable(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    created = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="intern",
        now=T0,
    )
    interview_id = created["interview_id"]
    start_role_interview(root, "learner-one", interview_id, catalog, now=T0)
    pause_role_interview(root, "learner-one", interview_id, now=T0 + timedelta(minutes=1))
    service = ApplicationService(root)
    assert service.resumable_interview("learner-one")["status"] == "paused"
    paused_context = build_interview_context(
        root, catalog, "learner-one", interview_id, now=T0 + timedelta(minutes=2)
    )
    assert paused_context["current"]["status"] == "paused"
    assert paused_context["current"]["question"]["question_id"] == "q-001"
    assert paused_context["current"]["remaining_seconds"] > 0
    assert paused_context["commands"]["next"].endswith(
        f"role-resume {interview_id} --profile learner-one"
    )

    path = profile_paths(root, "learner-one").interviews_root / interview_id / "session.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value.pop("paused_at", None)
    value.pop("paused_remaining_seconds", None)
    value["status"] = "active"
    value["deadline"] = "2026-08-28T10:15:00Z"
    path.write_text(json.dumps(value), encoding="utf-8")
    loaded = load_role_interview(root, "learner-one", interview_id)
    assert loaded["status"] == "active"


def test_plan_fingerprint_rejects_tampering(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="intern",
        now=T0,
    )
    path = (
        profile_paths(root, "learner-one").interviews_root
        / session["interview_id"]
        / "session.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    value["questions"][0]["prompt"] = "tampered"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(RoleInterviewError, match="plan changed"):
        load_role_interview(root, "learner-one", session["interview_id"])


def test_assessment_rejects_empty_or_noncanonical_answer_evidence(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        now=T0,
    )
    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    question = current_role_question(
        root, "learner-one", session["interview_id"], now=T0
    )["question"]
    record_role_answer(
        root,
        "learner-one",
        session["interview_id"],
        question["question_id"],
        "A valid answer that will retain its canonical file.",
        now=T0,
    )
    path = (
        profile_paths(root, "learner-one").interviews_root
        / session["interview_id"]
        / "session.json"
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    value["answers"][question["question_id"]]["relative_path"] = ""
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(RoleInterviewError, match="answer path is invalid"):
        record_role_assessment(
            root,
            "learner-one",
            session["interview_id"],
            question["question_id"],
            {name: 3 for name in question["rubric"]["dimensions"]},
            evidence="This must not be accepted without canonical answer evidence.",
            source="human",
            confidence="high",
            now=T0 + timedelta(minutes=1),
        )


def test_finish_rejects_answer_file_changed_after_assessment(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        now=T0,
    )
    interview_id = session["interview_id"]
    start_role_interview(root, "learner-one", interview_id, catalog, now=T0)
    question = current_role_question(root, "learner-one", interview_id, now=T0)["question"]
    assert question is not None and question["kind"] != "coding"
    record_role_answer(
        root,
        "learner-one",
        interview_id,
        question["question_id"],
        "Original locked answer with explicit evidence.",
        now=T0,
    )
    record_role_assessment(
        root,
        "learner-one",
        interview_id,
        question["question_id"],
        {name: 3 for name in question["rubric"]["dimensions"]},
        evidence="The original answer names evidence and trade-offs.",
        source="human",
        confidence="high",
        now=T0 + timedelta(minutes=1),
    )
    answer_path = (
        profile_paths(root, "learner-one").interviews_root
        / interview_id
        / "answers"
        / f"{question['question_id']}.md"
    )
    answer_path.write_text("Tampered after scoring.\n", encoding="utf-8")
    with pytest.raises(RoleInterviewError, match="locked answer changed"):
        finish_role_interview(
            root,
            "learner-one",
            interview_id,
            confirm_incomplete=True,
            now=T0 + timedelta(minutes=2),
        )


def test_role_interview_context_reads_only_explicit_sha_bound_material(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    source = tmp_path / "resume.md"
    source.write_text(
        "Synthetic candidate evidence: built a toy evaluator.\n", encoding="utf-8"
    )
    material = add_material(
        root,
        "learner-one",
        source,
        kind="resume",
        title="Synthetic resume",
        ai_access=True,
        material_id="resume-one",
    )
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        ai_mode="provider",
        material_ids=(material.id,),
        consent_materials=True,
        now=T0,
    )
    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    preview = build_role_interview_context_preview(
        root,
        "learner-one",
        session["interview_id"],
        candidate_answer="I would validate one measurable assumption first.",
        now=T0 + timedelta(minutes=1),
    )
    assert [part.id for part in preview.parts] == [
        "policy",
        "question",
        "material:resume-one",
        "candidate_answer",
    ]
    assert preview.parts[2].sensitive
    assert "toy evaluator" in preview.parts[2].content
    assert "learner-two" not in preview.selected_text
    without_material = build_role_interview_context_preview(
        root,
        "learner-one",
        session["interview_id"],
        candidate_answer="I would validate one measurable assumption first.",
        include_materials=False,
        now=T0 + timedelta(minutes=1),
    )
    assert [part.id for part in without_material.parts] == [
        "policy",
        "question",
        "candidate_answer",
    ]
    assert "toy evaluator" not in without_material.selected_text

    resolve_material_path(root, "learner-one", material).write_text(
        "changed after consent\n", encoding="utf-8"
    )
    with pytest.raises(ContextBuilderError, match="stale or revoked"):
        build_role_interview_context_preview(
            root,
            "learner-one",
            session["interview_id"],
            candidate_answer="Same answer.",
            now=T0 + timedelta(minutes=1),
        )


def test_paused_role_interview_context_is_read_only_and_recoverable(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        ai_mode="provider",
        now=T0,
    )
    interview_id = session["interview_id"]
    start_role_interview(root, "learner-one", interview_id, catalog, now=T0)
    pause_role_interview(root, "learner-one", interview_id, now=T0 + timedelta(minutes=1))

    preview = build_role_interview_context_preview(
        root, "learner-one", interview_id, now=T0 + timedelta(minutes=2)
    )
    assert "read-only" in preview.parts[0].content
    assert "q-001" in preview.parts[1].content


def test_role_interviewer_context_never_previews_future_question(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_product_manager",
        seniority="new_grad",
        now=T0,
    )
    first, second = session["questions"][:2]
    ready = build_interview_context(
        root, catalog, "learner-one", session["interview_id"], now=T0
    )
    assert first["prompt"] not in serialize_context(ready)
    assert second["prompt"] not in serialize_context(ready)

    start_role_interview(root, "learner-one", session["interview_id"], catalog, now=T0)
    active = build_interview_context(
        root,
        catalog,
        "learner-one",
        session["interview_id"],
        now=T0 + timedelta(minutes=1),
    )
    assert active["current"]["question"]["question_id"] == "q-001"
    assert active["current"]["question"]["prompt"] == first["prompt"]
    assert active["current"]["question"]["prompt"] != second["prompt"]

    record_role_answer(
        root,
        "learner-one",
        session["interview_id"],
        "q-001",
        "I state assumptions, a measurable outcome, and a reversible experiment.",
        now=T0 + timedelta(minutes=1),
    )
    awaiting_score = build_interview_context(
        root,
        catalog,
        "learner-one",
        session["interview_id"],
        now=T0 + timedelta(minutes=3),
    )
    assert awaiting_score["current"]["question"]["question_id"] == "q-001"
    assert awaiting_score["current"]["answer"]["path"].endswith("q-001.md")
    assert "role-score" in awaiting_score["commands"]["next"]
    assert awaiting_score["current"]["question"]["prompt"] != second["prompt"]

    record_role_assessment(
        root,
        "learner-one",
        session["interview_id"],
        "q-001",
        {name: 3 for name in first["rubric"]["dimensions"]},
        evidence="q-001 names assumptions and measurable evidence.",
        source="human",
        confidence="high",
        now=T0 + timedelta(minutes=2),
    )
    next_question = build_interview_context(
        root,
        catalog,
        "learner-one",
        session["interview_id"],
        now=T0 + timedelta(minutes=3),
    )
    assert next_question["current"]["question"]["question_id"] == "q-002"
