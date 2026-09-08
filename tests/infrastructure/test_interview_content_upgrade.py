"""Reviewed depth guidance and report actions use real, unchanged public assets."""
import hashlib
import json

from tests.infrastructure.test_unified_interview import public_repo, unified, create
from tests.infrastructure.test_question_first_interview import advance
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab.role_interviews import dynamic_coding_candidates, update_finished_grading
from llm_interview_lab.desktop.coding_statements_zh import chinese_statement

CARDS = [f"EGT-QB-{n:03}" for n in (1, 2, 7, 11, 14, 19, 21, 25, 26, 28, 29, 30, 37, 48, 58, 68)]
PROBLEMS = "OPT-002 LOSS-014 LOSS-016 NNL-018 NNL-008 ATT-019 ATT-021 ATT-020 PT-003 PT-022 PT-023 PT-010".split()


def test_all_reviewed_cards_and_task_versions_are_reachable(unified):
    service, profile = unified
    knowledge = service.knowledge_catalog()
    for cid in CARDS:
        card = knowledge.get(cid)
        guidance = card.raw["interview_guidance"]
        assert set(guidance) == {"entry_signals", "deepen", "weak_answer", "variations", "stop_when"}
        assert all(guidance.values())
        assert knowledge.related_coding_problems(cid)
        payload = service.knowledge_card_view(cid)
        assert payload["interview_guidance"] == guidance
    eligible = set()
    for role in ("ai_algorithm_research_engineer", "post_training_engineer"):
        for difficulty in ("easy", "medium", "hard"):
            session = create(service, profile, role_id=role, difficulty=difficulty)
            eligible.update(p.id for p, _ in dynamic_coding_candidates(service.catalog, service.roles, session))
    for pid in PROBLEMS:
        problem = service.catalog.get(pid)
        assert pid in eligible, pid
        statement = (problem.problem_dir / "task.md").read_text(encoding="utf-8")
        review = knowledge.coding_review(pid, statement)
        assert review and review["task_sha256"] == hashlib.sha256(statement.encode()).hexdigest()
        assert not knowledge.coding_review(pid, statement + "\nchanged contract")
        assert len(chinese_statement(pid, statement)) > 100
        assert all(service.catalog.get(p).ready for c in review["knowledge_ids"] for p in knowledge.related_coding_problems(c) if p in PROBLEMS)
        assert (problem.problem_dir / "starter.py").is_file()
        assert (problem.problem_dir / "test_public.py").is_file()


def test_real_next_question_context_contains_guidance_not_answers(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    advance(service, profile, iid, "experience")
    advance(service, profile, iid, "theory")
    preview = build_role_interview_context_preview(service.repo_root, profile, iid,
        candidate_answer="GRPO 的组内优势、长度归约和 KL 我分别验证过。", include_materials=False,
        catalog=service.catalog, role_catalog=service.roles, knowledge=service.knowledge_catalog())
    pool = json.loads(next(p.content for p in preview.parts if p.id == "knowledge_candidates"))
    assert any(card["interview_guidance"] for card in pool["cards"])
    assert all("core_answer" not in card and "answer_outline" not in card for card in pool["cards"])


def test_report_links_missing_evidence_without_rewriting_interview(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    service.answer_interview(profile, iid, "q-001", "我使用独立评测集验证合成研究。")
    service.finish_interview(profile, iid, confirm_incomplete=True)
    report = service.interview_result_view(profile, iid)
    assert "seniority" not in report
    assert not report["strengths"] and len(report["learning_gaps"]) == 3
    assert report["coverage"]["missing_stages"]
    original = service.interview_session(profile, iid)
    for gap in report["learning_gaps"]:
        for card in gap["knowledge"]:
            assert service.knowledge_card_view(card["id"])
        for problem in gap["practice"]:
            assert service.catalog.get(problem["id"])
            assert problem["available"] or problem["reason"]
    first = original["questions"][0]
    update_finished_grading(service.repo_root, profile, iid, "q-001", result={
        "scores": {d: 4 for d in first["rubric"]["dimensions"]},
        "evidence": "回答明确说明使用独立评测集验证方法，但还需要数据隔离的具体证据。", "evidence_quote": "独立评测集",
        "confidence": "medium", "fatal_issues": [], "follow_up": ""})
    report = service.interview_result_view(profile, iid)
    assert report["strengths"][0]["question_id"] == "q-001"
    assert report["overall_score"] < 75  # no renormalization over just one completed stage
    after = service.interview_session(profile, iid)
    assert after["answers"] == original["answers"]
    assert after["result"]["finished_at"] == original["result"]["finished_at"]


def test_finished_coding_review_uses_frozen_code_and_guidance(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    advance(service, profile, iid, "experience")
    advance(service, profile, iid, "theory")
    session = advance(service, profile, iid, "coding")
    q = session["questions"][-1]
    service.save_interview_coding_submission(profile, iid, "# partial implementation\nprint([1, 2])")
    service.lock_interview_code(profile, iid)
    service.finish_interview(profile, iid, confirm_incomplete=True)
    preview = build_role_interview_context_preview(service.repo_root, profile, iid,
        include_materials=False, assessment_question_id=q["question_id"])
    policy = next(p.content for p in preview.parts if p.id == "policy")
    assert "next_stage" not in policy
    if q["source"]["id"] in PROBLEMS:
        assert any(p.id == "coding_review" for p in preview.parts)
    session = service.interview_session(profile, iid)
    dialogue = service.interview_dialogue(profile, session)
    assert dialogue[-1]["answer"] == "# partial implementation\nprint([1, 2])"
    assert "submission_sha256" not in dialogue[-1]["answer"]
    scores = {d: 1 for d in q["rubric"]["dimensions"]}
    assessed = update_finished_grading(service.repo_root, profile, iid, q["question_id"], result={
        "scores": scores, "evidence": "代码只是输出列表，没有实现当前算法；退出码不能证明算法正确。",
        "evidence_quote": "# partial implementation\nprint([1, 2])",
        "confidence": "high", "fatal_issues": [], "follow_up": ""})
    assert assessed["assessments"][q["question_id"]]["source"] == "ai"
    assert not assessed["coding_evidence"]
