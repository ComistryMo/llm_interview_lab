"""The v2 contract: question-first, time-aware, stage-free, deferred evidence scoring."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from tests.infrastructure.test_unified_interview import public_repo, unified, create
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab.interview_flow import next_stages, flow_coverage, streamed_question
from llm_interview_lab.role_interviews import (
    RoleInterviewError, dynamic_coding_candidates, set_role_ai_wait,
    start_role_interview, current_role_question, pause_role_interview,
    resume_role_interview, record_role_answer, update_finished_grading,
)


def decision(service, session, stage, *, angle="", topic="", sufficient=False):
    candidates = dynamic_coding_candidates(service.catalog, service.roles, session)
    return {"next_stage": stage, "follow_up": "你刚才提到独立评测集，能说说如何避免训练数据泄漏吗？" if stage in {"experience", "theory"} else "",
            "coding_problem_id": candidates[0][0].id if stage == "coding" else "",
            "next_skill_ids": [next(iter(service.roles.roles[session["role_id"]].skill_weights))] if stage in {"experience", "theory"} else [],
            "coverage": {"experience": "合成研究项目", "angle": angle, "topic": topic,
                         "evidence": "独立评测集" if sufficient else "", "sufficient": sufficient}}


def advance(service, profile, iid, stage, **coverage):
    session = service.interview_session(profile, iid)
    qid = session["questions"][-1]["question_id"]
    if session["questions"][-1]["kind"] == "coding":
        service.save_interview_coding_submission(profile, iid, "# 独立评测集\nprint([1, 2])")
        service.lock_interview_code(profile, iid)
    else:
        service.answer_interview(profile, iid, qid, "合成回答：我使用独立评测集排除了训练数据泄漏。")
    session = service.interview_session(profile, iid)
    return service.advance_dynamic_interview(profile, iid, qid, decision(service, session, stage, **coverage), context_sha256="a" * 64)


@pytest.mark.parametrize("role", ["ai_algorithm_research_engineer", "post_training_engineer"])
@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
@pytest.mark.parametrize("sufficient", [True, False])
def test_twelve_coverage_trajectories_and_deferred_scoring(unified, role, difficulty, sufficient):
    service, profile = unified
    session = create(service, profile, role_id=role, difficulty=difficulty)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    session = advance(service, profile, iid, "experience")
    angles = ["实现", "选择依据"] + (["消融验证"] if difficulty != "easy" else [])
    for index, angle in enumerate(angles):
        session = advance(service, profile, iid, "theory" if index == len(angles) - 1 else "experience", angle=angle, sufficient=sufficient)
    topics = ["优化目标", "数值稳定", "Attention"] + (["替代解释"] if difficulty == "hard" else [])
    for index, topic in enumerate(topics):
        session = advance(service, profile, iid, "coding" if index == len(topics) - 1 else "theory", topic=topic, sufficient=sufficient)
    assert session["questions"][-1]["kind"] == "coding"
    assert not session["assessments"]
    assert "seniority" not in session
    session = advance(service, profile, iid, "finish")
    assert service.current_interview(profile, iid)["question"] is None
    coverage = flow_coverage(session)
    assert coverage["complete"] is sufficient
    finished = service.finish_interview(profile, iid, confirm_incomplete=True)
    assert not finished["assessments"] and finished["result"]["unscored"]
    original_finished = finished["result"]["finished_at"]
    for q in finished["questions"]:
        result = {"scores": {d: 3 for d in q["rubric"]["dimensions"]},
                  "evidence": "本题回答描述了独立评测思路；实现细节仍缺少更完整证据。",
                  "evidence_quote": "独立评测集", "confidence": "medium", "fatal_issues": [], "follow_up": ""}
        finished = update_finished_grading(service.repo_root, profile, iid, q["question_id"], result=result)
    assert finished["result"]["overall_score"] == 50
    assert finished["result"]["finished_at"] == original_finished
    assert finished["status"] == ("completed" if sufficient else "incomplete")
    assert all(v["status"] == "complete" for v in finished["grading"]["questions"].values())


def test_wait_pause_retry_and_restart_do_not_charge_twice(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start_role_interview(service.repo_root, profile, iid, service.catalog, now=now)
    record_role_answer(service.repo_root, profile, iid, "q-001", "我负责合成实验的实现与评测。", now=now + timedelta(seconds=10))
    set_role_ai_wait(service.repo_root, profile, iid, True, now=now + timedelta(seconds=10))
    state = current_role_question(service.repo_root, profile, iid, now=now + timedelta(seconds=130))
    assert state["remaining_seconds"] == 3590
    paused = pause_role_interview(service.repo_root, profile, iid, now=now + timedelta(seconds=130))
    assert paused["paused_remaining_seconds"] == 3590
    assert paused["ai_wait_seconds"] == 120 and "ai_wait_started_at" not in paused
    resume_role_interview(service.repo_root, profile, iid, now=now + timedelta(seconds=200))
    assert current_role_question(service.repo_root, profile, iid, now=now + timedelta(seconds=210))["remaining_seconds"] == 3580
    set_role_ai_wait(service.repo_root, profile, iid, True, now=now + timedelta(seconds=210))
    set_role_ai_wait(service.repo_root, profile, iid, False, now=now + timedelta(seconds=230))
    set_role_ai_wait(service.repo_root, profile, iid, False, now=now + timedelta(seconds=250))
    assert current_role_question(service.repo_root, profile, iid, now=now + timedelta(seconds=250))["remaining_seconds"] == 3560


def test_no_minimum_turn_count_and_reserve_coding_time(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    session = advance(service, profile, iid, "experience")
    assert next_stages(session, coding_available=True) == ["experience", "theory"]
    started = datetime.fromisoformat(session["started_at"].replace("Z", "+00:00"))
    assert next_stages(session, coding_available=True, now=started + timedelta(minutes=28)) == ["theory"]
    assert next_stages(session, coding_available=True, now=started + timedelta(minutes=43)) == ["coding"]


def test_new_request_has_no_scores_or_stage_bucket_and_rejects_invented_id(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    advance(service, profile, iid, "experience")
    session = advance(service, profile, iid, "theory")
    qid = session["questions"][-1]["question_id"]
    service.answer_interview(profile, iid, qid, "独立评测集用于验证，不参与参数更新。")
    preview = build_role_interview_context_preview(service.repo_root, profile, iid, candidate_answer="独立评测集用于验证，不参与参数更新。", include_materials=False)
    policy = next(p.content for p in preview.parts if p.id == "policy")
    contract = json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))
    assert "stage_minimums" not in contract and "seniority" not in contract
    assert "coverage_targets" in contract and "scores" not in policy
    malformed = decision(service, session, "coding")
    malformed["coding_problem_id"] = "INVENTED-999"
    with pytest.raises(RoleInterviewError, match="可运行候选"):
        service.advance_dynamic_interview(profile, iid, qid, malformed, context_sha256="a" * 64)
    assert service.current_interview(profile, iid)["question"]["question_id"] == qid


def test_streaming_extracts_only_display_text():
    assert streamed_question('{"follow_up":"你刚才说\\n独立') == "你刚才说\n独立"
    assert streamed_question('{"scores":{"a":3},"reasoning":"内部文本"') == ""
    assert streamed_question('{"follow_up":"你好","next_stage":"theory"}') == "你好"
