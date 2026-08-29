from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
from llm_interview_lab.context import build_interview_context, serialize_context
from llm_interview_lab.materials import add_material, resolve_material_path
from llm_interview_lab.role_interviews import (
    RoleInterviewError,
    create_role_interview,
    current_role_question,
    finish_role_interview,
    load_role_interview,
    record_role_answer,
    record_role_assessment,
    record_role_followup,
    role_interview_report,
    start_role_interview,
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
    report = role_interview_report(root, "learner-one", session["interview_id"])
    assert "Practice mastery: **unchanged**" in report
    assert "offer probability" in report


def test_role_blueprint_selects_validated_coding_problem_and_creates_local_starter(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    catalog, roles = _catalogs(root)
    session = create_role_interview(
        root,
        "learner-one",
        catalog,
        roles,
        role_id="ai_algorithm_research_engineer",
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
    with pytest.raises(RoleInterviewError, match="does not exist"):
        load_role_interview(root, "learner-two", one["interview_id"])


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
