"""Protocol 3 deterministic tests. Only synthetic, isolated profiles."""
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from tests.infrastructure.test_unified_interview import public_repo, unified, create
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview
from llm_interview_lab import interviewer_state
from llm_interview_lab.role_interviews import RoleInterviewError, pause_role_interview, resume_role_interview

BASELINE = Path(__file__).parents[1] / "fixtures/interviewer-v2-baseline.json"


def test_v2_compiled_baseline(unified):
    service, profile = unified
    session = create(service, profile)
    iid = session["interview_id"]
    service.start_interview(profile, iid)
    answer = "合成经历：我负责 GRPO 训练中的组内优势计算，用独立评测集比较消融。"
    service.answer_interview(profile, iid, "q-001", answer)
    preview = build_role_interview_context_preview(
        service.repo_root, profile, iid, candidate_answer=answer,
        include_materials=False, catalog=service.catalog, role_catalog=service.roles,
    )
    parts = {part.id: part.content for part in preview.parts}
    if os.environ.get("LLM_LAB_CAPTURE_V2_BASELINE") == "1":
        assert not BASELINE.exists(), "Historical baseline must not be overwritten"
        BASELINE.parent.mkdir(exist_ok=True)
        BASELINE.write_text(json.dumps({
            "source_sha": "b954c71d6a7029010fc247cbf7eef6c880a102f1",
            "interaction_version": 2, "synthetic": True, "parts": parts,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    # The original capture includes a randomly named *synthetic* profile.
    # Keep its bytes intact and normalize only this non-policy fixture field.
    background = json.loads(parts["profile_context"])
    background["display_name"] = json.loads(baseline["parts"]["profile_context"])["display_name"]
    parts["profile_context"] = json.dumps(background, ensure_ascii=False, indent=2)
    assert parts == baseline["parts"]


def new_v3(service, profile):
    session = service.create_dynamic_interview(profile, role_id="post_training_engineer", difficulty="hard",
        ai_mode="provider", initial_question={"kind": "oral", "title": "自我介绍",
            "prompt": "请介绍你本人在合成训练实验中负责的工作。", "source_kind": "process_opening"},
        context_sha256="a" * 64)
    service.start_interview(profile, session["interview_id"])
    return session["interview_id"]


def context(service, profile, iid, answer):
    preview = build_role_interview_context_preview(service.repo_root, profile, iid,
        candidate_answer=answer, include_materials=False, catalog=service.catalog, role_catalog=service.roles)
    return json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))


def packet(contract, *, intro=True, status="partial", criterion="mechanism", claim_ref="new:claim", experience_ref="new:exp"):
    topic = contract["role_skills"][0]["id"]
    qid = contract["request_basis"]["question_id"]
    evidence = {"question_id": qid, "quote": "我负责组内优势计算"}
    return {"follow_up": "你能介绍一下这个训练实验中组内优势具体是如何计算的吗？",
        "next_stage": "experience", "coding_problem_id": "", "next_skill_ids": [topic],
        "state_update": {
            "experiences": [{"ref": experience_ref, "label": "合成训练实验", "evidence": evidence}] if experience_ref.startswith("new:") else [],
            "claims": [{"ref": claim_ref, "experience_ref": experience_ref, "topic_id": topic,
                        "angle": "mechanism", "criterion": criterion, "statement": "候选人负责组内优势",
                        "status": status, "assessment_note": "已提到负责计算，仍需核实具体实现。", "evidence": evidence}],
            "contradictions": [], "closures": []},
        "probe": {"claim_ref": claim_ref, "topic_id": topic, "criterion": criterion, "method_id": "core",
                  "knowledge_ids": [], "action": "invite" if intro else "inspect"},
        "transition_reason": "introduction_complete" if intro else "continue"}


def commit(service, profile, iid, contract, value):
    return service.advance_dynamic_interview(profile, iid, contract["request_basis"]["question_id"],
        value, context_sha256="b" * 64, request_contract=contract)


def test_v3_actual_service_transaction_retry_restart_and_provenance(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算，使用组内均值作为基线。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    assert contract["interaction_version"] == 3
    assert "sufficient" not in contract.get("observed_coverage", {})
    result = commit(service, profile, iid, contract, packet(contract))
    assert result["interviewer_state"]["revision"] == 1
    quote = result["interviewer_state"]["claims"]["claim-0001"]["evidence"][0]
    assert answer[quote["start"]:quote["end"]] == quote["quote"]
    assert quote["answer_sha256"] == result["answers"]["q-001"]["sha256"]
    assert quote["quote_verified"] is True
    assert result["interviewer_state"]["claims"]["claim-0001"]["criterion_status"] == "partial"
    assert not result["assessments"]
    assert service.current_interview(profile, iid)["question"]["question_id"] == "q-002"
    with pytest.raises(RoleInterviewError):
        commit(service, profile, iid, contract, packet(contract))
    restored = type(service)(service.repo_root).interview_session(profile, iid)
    assert restored == result


@pytest.mark.parametrize("damage", ["hash", "quote", "missing_claim", "missing_answer", "version", "gap_criterion"])
def test_corrupt_recovery_never_rebuilds(unified, damage):
    from llm_interview_lab.role_interviews import _session_root
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    session = commit(service, profile, iid, contract, packet(contract))
    state = session["interviewer_state"]
    if damage == "hash":
        state["claims"]["claim-0001"]["evidence"][0]["answer_sha256"] = "0" * 64
    elif damage == "quote":
        state["claims"]["claim-0001"]["evidence"][0]["quote"] = "你负责组内优势计算"
    elif damage == "missing_claim":
        state["claims"].clear()
    elif damage == "missing_answer":
        session["answers"].clear()
    elif damage == "gap_criterion":
        state["gaps"]["claim-0001"]["criterion"] = "ratio"
    else:
        state["schema_version"] = 99
    path = _session_root(service.repo_root, profile, iid) / "session.json"
    path.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(RoleInterviewError):
        type(service)(service.repo_root).interview_session(profile, iid)
    assert path.read_bytes() == before


def test_model_cannot_authorize_user_skip(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    value = packet(contract)
    value["state_update"]["closures"] = [{"claim_ref": "new:claim", "reason": "user_skip",
        "evidence": {"question_id": "q-001", "quote": answer}}]
    with pytest.raises(RoleInterviewError, match="不能代替"):
        commit(service, profile, iid, contract, value)
    assert service.interview_session(profile, iid)["interviewer_state"]["revision"] == 0


@pytest.mark.parametrize("bad", ["改写数字", "拼接", "跨题", "版本", "跨档案", "方法", "未加载方法", "知识", "主张", "转场"])
def test_invalid_decision_cannot_write_state_or_question(unified, bad):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。系数为0.3。评测集独立。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    value = packet(contract)
    if bad == "改写数字":
        value["state_update"]["claims"][0]["evidence"]["quote"] = "系数为0.8"
    elif bad == "拼接":
        value["state_update"]["claims"][0]["evidence"]["quote"] = "我负责…评测集独立"
    elif bad == "跨题":
        value["state_update"]["claims"][0]["evidence"]["question_id"] = "q-999"
    elif bad == "版本":
        contract["request_basis"]["state_revision"] += 1
    elif bad == "跨档案":
        contract["request_basis"]["profile_id"] = "another-synthetic-profile"
    elif bad == "方法":
        value["probe"]["method_id"] = "invented"
    elif bad == "未加载方法":
        from llm_interview_lab.interview_expertise import METHODS
        value["probe"]["method_id"] = next(m for m in METHODS if m not in contract["loaded_method_ids"])
    elif bad == "知识":
        value["probe"]["knowledge_ids"] = ["UNLOADED"]
    elif bad == "主张":
        value["state_update"]["claims"][0]["experience_ref"] = "exp-9999"
    else:
        value["next_stage"] = "theory"
        value["transition_reason"] = "sufficient"
    before = service.interview_session(profile, iid)
    with pytest.raises((ValueError, RoleInterviewError)):
        commit(service, profile, iid, contract, value)
    assert service.interview_session(profile, iid) == before
    assert service.interview_answer_text(profile, iid, "q-001") == answer


def test_pause_resume_invalidates_same_answer_request(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    pause_role_interview(service.repo_root, profile, iid)
    resume_role_interview(service.repo_root, profile, iid)
    with pytest.raises(RoleInterviewError, match="已变化"):
        commit(service, profile, iid, contract, packet(contract))
    new = context(service, profile, iid, answer)
    assert commit(service, profile, iid, new, packet(new))["interviewer_state"]["revision"] == 1


def test_paraphrase_reuses_claim_and_distinct_grpo_criteria_do_not_collide(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    contract = context(service, profile, iid, answer)
    commit(service, profile, iid, contract, packet(contract, criterion="advantage"))
    for qid, criterion in (("q-002", "advantage"), ("q-003", "ratio"), ("q-004", "reduction")):
        service.answer_interview(profile, iid, qid, answer)
        contract = context(service, profile, iid, answer)
        value = packet(contract, intro=False, criterion=criterion, experience_ref="exp-0001")
        value["state_update"]["claims"][0]["statement"] = "这是对同一工作的新表述"
        result = commit(service, profile, iid, contract, value)
    assert len(result["interviewer_state"]["claims"]) == 3
    assert result["interviewer_state"]["revision"] == 4


def test_current_answer_closes_gap_before_transition_is_checked():
    # The merge, not the state at request start, determines this transition.
    topic = "grpo"
    session = {"profile_id": "synthetic", "interview_id": "role-interview-0001", "status": "active",
        "difficulty": "hard", "questions": [{"question_id": "q-004", "stage": "experience"}],
        "answers": {"q-004": {"sha256": "a" * 64}}, "timeline": [], "interviewer_state": interviewer_state.empty_state()}
    for i, (angle, criterion) in enumerate((("mechanism", "mechanism"), ("implementation", "implementation"), ("evaluation", "validation")), 1):
        key = f"claim-{i:04d}"
        session["interviewer_state"]["claims"][key] = {
            "experience_id": "", "topic_id": topic, "criterion": criterion, "angle": angle, "stage": "experience",
            "statement": "合成主张", "criterion_status": "model_supported" if i < 3 else "partial",
            "evidence": [{"question_id": "q-004"}]}
        session["interviewer_state"]["gaps"][key] = {"status": "closed" if i < 3 else "open"}
    contract = {"role_skills": [{"id": topic}], "request_basis": interviewer_state.request_basis(session, "q-004")}
    value = packet(contract, intro=False, status="model_supported", criterion="validation",
                   claim_ref="claim-0003", experience_ref="")
    value.update(next_stage="theory", transition_reason="sufficient")
    value["probe"]["action"] = "transition"
    merged = interviewer_state.merge_decision(session, value, contract["request_basis"],
        {"q-004": ("我负责组内优势计算", "a" * 64)}, allowed_topics={topic}, allowed_knowledge=[])
    assert merged["gaps"]["claim-0003"]["status"] == "closed"
    assert session["interviewer_state"]["gaps"]["claim-0003"]["status"] == "open"


def test_unknown_adjacent_probe_closes_without_claiming_support(unified):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算，但具体原理不清楚。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    commit(service, profile, iid, c, packet(c))
    service.answer_interview(profile, iid, "q-002", answer)
    c = context(service, profile, iid, answer)
    value = packet(c, intro=False, status="explicit_unknown", claim_ref="claim-0001", experience_ref="exp-0001")
    value["state_update"]["claims"][0]["evidence"]["quote"] = "具体原理不清楚"
    value["probe"]["action"] = "adjacent"
    commit(service, profile, iid, c, value)
    service.answer_interview(profile, iid, "q-003", answer)
    c = context(service, profile, iid, answer)
    value = packet(c, intro=False, status="explicit_unknown", claim_ref="claim-0001", experience_ref="exp-0001")
    value["state_update"]["claims"][0]["evidence"]["quote"] = "具体原理不清楚"
    value["state_update"]["closures"] = [{"claim_ref": "claim-0001", "reason": "confirmed_unknown",
        "evidence": {"question_id": "q-003", "quote": "具体原理不清楚"}}]
    new = deepcopy(value["state_update"]["claims"][0])
    new.update(ref="new:implementation", criterion="implementation", status="unassessed")
    value["state_update"]["claims"].append(new)
    value["probe"].update(claim_ref="new:implementation", criterion="implementation", action="change_angle")
    result = commit(service, profile, iid, c, value)
    assert result["interviewer_state"]["gaps"]["claim-0001"]["status"] == "closed"
    assert result["interviewer_state"]["claims"]["claim-0001"]["criterion_status"] == "explicit_unknown"
    from llm_interview_lab.interview_flow import flow_coverage
    assert not flow_coverage(result)["experience_angles"]


def test_time_transition_preserves_unresolved_gaps(unified):
    from llm_interview_lab.role_interviews import advance_dynamic_role_interview
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    commit(service, profile, iid, c, packet(c))
    service.answer_interview(profile, iid, "q-002", answer)
    c = context(service, profile, iid, answer)
    value = packet(c, intro=False, claim_ref="claim-0001", experience_ref="exp-0001")
    value.update(next_stage="theory", transition_reason="time_deferred")
    value["probe"]["action"] = "transition"
    started = datetime.fromisoformat(service.interview_session(profile, iid)["started_at"].replace("Z", "+00:00"))
    result = advance_dynamic_role_interview(service.repo_root, profile, iid, service.catalog, service.roles,
        "q-002", value, context_sha256="b" * 64, request_contract=c, now=started + timedelta(minutes=28))
    assert result["questions"][-1]["stage"] == "theory"
    assert result["interviewer_state"]["gaps"]["claim-0001"]["status"] == "open"
    assert result["turn_decisions"]["q-002"]["transition_reason"] == "time_deferred"


@pytest.mark.parametrize("alias", [False, True])
def test_contradiction_cannot_relabel_supported_without_resolution(unified, alias):
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算，系数是0.3。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    commit(service, profile, iid, c, packet(c))
    answer = "我负责组内优势计算，系数是0.8。"
    service.answer_interview(profile, iid, "q-002", answer)
    c = context(service, profile, iid, answer)
    value = packet(c, intro=False, status="disputed", claim_ref="claim-0001", experience_ref="exp-0001")
    value["state_update"]["contradictions"] = [{"claim_ref": "claim-0001",
        "first": {"question_id": "q-001", "quote": "系数是0.3"},
        "second": {"question_id": "q-002", "quote": "系数是0.8"},
        "ambiguity": "尚未说明是否来自不同实验。", "resolved": False, "resolution": ""}]
    commit(service, profile, iid, c, value)
    service.answer_interview(profile, iid, "q-003", answer)
    c = context(service, profile, iid, answer)
    value = packet(c, intro=False, status="model_supported", claim_ref="claim-0001", experience_ref="exp-0001")
    if alias:
        value = packet(c, intro=False, status="model_supported", claim_ref="new:renamed-claim", experience_ref="new:renamed-experience")
    with pytest.raises(RoleInterviewError, match="消歧"):
        commit(service, profile, iid, c, value)


def test_atomic_save_failure_keeps_answer_and_previous_state(unified, monkeypatch):
    import llm_interview_lab.role_interviews as domain
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    before = service.interview_session(profile, iid)
    def fail_save(*args):
        raise RoleInterviewError("synthetic storage failure")
    monkeypatch.setattr(domain, "_atomic_write", fail_save)
    with pytest.raises(RoleInterviewError, match="synthetic"):
        commit(service, profile, iid, c, packet(c))
    assert service.interview_session(profile, iid) == before
    assert service.interview_answer_text(profile, iid, "q-001") == answer
    monkeypatch.undo()
    result = commit(service, profile, iid, c, packet(c))
    assert result["interviewer_state"]["revision"] == 1


def test_v3_finished_grading_does_not_mutate_evidence_or_repeat_scores(unified):
    from llm_interview_lab.role_interviews import update_finished_grading
    service, profile = unified
    iid = new_v3(service, profile)
    answer = "我负责组内优势计算。"
    service.answer_interview(profile, iid, "q-001", answer)
    c = context(service, profile, iid, answer)
    saved = commit(service, profile, iid, c, packet(c))
    ended = service.finish_interview(profile, iid, confirm_incomplete=True)
    assert ended["grading"]["questions"]["q-001"]["status"] == "pending"
    result = {"scores": {k: 3 for k in ended["questions"][0]["rubric"]["dimensions"]},
        "evidence": "候选人说明了本人负责的计算环节，但缺少公式、实现和验证的具体证据。",
        "evidence_quote": "我负责组内优势计算", "confidence": "medium", "fatal_issues": [], "follow_up": ""}
    graded = update_finished_grading(service.repo_root, profile, iid, "q-001", result=result)
    assert graded["interviewer_state"] == saved["interviewer_state"]
    assert graded["status"] == "incomplete"
    assert update_finished_grading(service.repo_root, profile, iid, "q-001", result=result) == graded


def test_empty_claim_and_invalid_quote_do_not_leak_response_in_traceback():
    import traceback
    marker = "PRIVATE-SYNTHETIC-ANSWER"
    with pytest.raises(ValueError) as caught:
        interviewer_state.decode_decision(json.dumps({"private": marker}))
    assert marker not in "".join(traceback.format_exception(caught.value))


def test_v3_cli_context_does_not_offer_premature_scoring(unified):
    import shutil
    from llm_interview_lab.context import build_interview_context
    service, profile = unified
    shutil.copy2(Path(__file__).parents[2] / "AGENTS.md", service.repo_root / "AGENTS.md")
    iid = new_v3(service, profile)
    service.answer_interview(profile, iid, "q-001", "我负责组内优势计算。")
    view = build_interview_context(service.repo_root, service.catalog, profile, iid)
    assert not any("role-score" in command for command in view["commands"].values())
    assert "同一事务" in view["current"]["continuation"]
    with pytest.raises(RoleInterviewError, match="结束后"):
        service.score_interview(profile, iid, "q-001", {},
            evidence="这是一段合成证据说明，不应提前评分。", source="ai", confidence="medium", fatal_issues=[])
