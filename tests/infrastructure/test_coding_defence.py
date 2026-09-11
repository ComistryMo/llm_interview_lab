"""Synthetic service trajectories; no model or additional code execution."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import pytest
from tests.infrastructure.test_interviewer_evidence import unified, public_repo, new_v3, context, packet, commit
from llm_interview_lab import role_interviews as ri
from llm_interview_lab.ai.context_builder import build_role_interview_context_preview

CODE = "def example(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n"


def coding_scene(service, profile, *, problem_id=None, coding_defence=True):
    if coding_defence:
        iid = new_v3(service, profile)
    else:
        old=service.create_dynamic_interview(profile,role_id="post_training_engineer",difficulty="hard",ai_mode="provider",
            initial_question={"kind":"oral","title":"旧协议","prompt":"请介绍你在合成实验中的具体工作。"},
            context_sha256="a"*64,coding_defence=False)
        iid=old["interview_id"]
        service.start_interview(profile,iid)
    start = datetime.fromisoformat(service.interview_session(profile, iid)["started_at"].replace("Z", "+00:00"))
    for i, (stage, minute) in enumerate((("experience", 0), ("theory", 30), ("coding", 43))):
        qid = f"q-{i+1:03d}"
        answer = "我负责组内优势计算。"
        service.answer_interview(profile, iid, qid, answer)
        c = context(service, profile, iid, answer)
        value = packet(c, intro=i == 0, claim_ref="new:claim" if i == 0 else "claim-0001", experience_ref="new:exp" if i == 0 else "exp-0001")
        if i:
            value.update(next_stage=stage, transition_reason="time_deferred")
            value["probe"]["action"] = "transition"
        if stage == "coding":
            candidates = ri.dynamic_coding_candidates(service.catalog, service.roles, service.interview_session(profile, iid))
            problem = next(p for p, _ in candidates if p.id == problem_id) if problem_id else candidates[0][0]
            value.update(follow_up="", next_skill_ids=[], coding_problem_id=problem.id)
        ri.advance_dynamic_role_interview(service.repo_root, profile, iid, service.catalog, service.roles,
            qid, value, context_sha256="b" * 64, request_contract=c, now=start + timedelta(minutes=minute))
    return iid


def defence_packet(c, *, finish=False, first=True):
    qid = c["request_basis"]["question_id"]
    value = packet(c, intro=False, criterion="implementation", claim_ref="new:code" if first else "claim-0002", experience_ref="")
    value.update(next_stage="finish" if finish else "coding", coding_problem_id="", next_skill_ids=[],
        follow_up="" if finish else "你在 total += x 这里如何保证累加结果与输入边界一致？",
        transition_reason="sufficient" if finish else "continue")
    value["state_update"]["claims"][0].update(
        statement="当前累加实现的边界待核实", status="model_supported" if finish else "partial",
        evidence={"question_id": "code:" + qid if first else qid, "quote": "total += x" if first else "空列表返回零"})
    value["probe"].update(method_id="code-defense-failure-analysis", action="transition" if finish else "inspect")
    return value


@pytest.mark.parametrize("two", [False, True])
def test_code_defence_parent_scoring_and_final_answer(unified, two):
    service, profile = unified
    iid = coding_scene(service, profile)
    service.save_interview_coding_submission(profile, iid, CODE)
    locked = service.lock_interview_code(profile, iid)
    parent = locked["coding_defence"]["parent_question_id"]
    digest = locked["coding_defence"]["submission_sha256"]
    assert digest == hashlib.sha256(CODE.encode()).hexdigest()
    c = context(service, profile, iid, service.interview_answer_text(profile, iid, parent))
    assert c["coding_candidates"] == [] and c["source_registry"][0]["kind"] == "locked_code"
    assert "code-defense-failure-analysis" in c["loaded_method_ids"]
    saved = commit(service, profile, iid, c, defence_packet(c))
    qid = saved["questions"][-1]["question_id"]
    assert saved["questions"][-1]["parent_coding_question_id"] == parent
    service.answer_interview(profile, iid, qid, "空列表返回零，但我还没有验证其他边界。")
    c = context(service, profile, iid, "空列表返回零，但我还没有验证其他边界。")
    service = type(service)(service.repo_root)
    assert service.interview_session(profile, iid)["interviewer_state"]["revision"] == saved["interviewer_state"]["revision"]
    saved = commit(service, profile, iid, c, defence_packet(c, first=False, finish=not two))
    if two:
        last = saved["questions"][-1]["question_id"]
        saved = service.answer_interview(profile, iid, last, "这里应该改成其他形式；这只是口头改法，没有执行。")
        assert saved["coding_defence"]["status"] == "closed"
        assert last not in saved["interviewer_state"]["applied_answers"]
        from llm_interview_lab.ai.context_builder import ContextBuilderError
        with pytest.raises(ContextBuilderError,match="收尾"):
            context(service,profile,iid,None)
    result = ri.finish_role_interview(service.repo_root, profile, iid, confirm_incomplete=True)
    service = type(service)(service.repo_root)
    assert service.interview_session(profile,iid)["grading"] == result["grading"]
    assert result["coding_defence"]["submission_sha256"] == digest
    children = set(result["coding_defence"]["question_ids"])
    assert not children & set(result["grading"]["questions"])
    assert parent in result["grading"]["questions"]
    from llm_interview_lab.ai.context_builder import ContextBuilderError
    with pytest.raises(ContextBuilderError,match="不独立评分"):
        build_role_interview_context_preview(service.repo_root,profile,iid,assessment_question_id=sorted(children)[0],include_materials=False)
    preview = build_role_interview_context_preview(service.repo_root, profile, iid, assessment_question_id=parent,
        include_materials=False, catalog=service.catalog, role_catalog=service.roles)
    assert "空列表返回零" in preview.selected_text
    if two:
        assert "这只是口头改法，没有执行" in preview.selected_text
    assert ri.finish_role_interview(service.repo_root, profile, iid, confirm_incomplete=True) == result
    for q in result["questions"]:
        qid = q["question_id"]
        if q.get("parent_coding_question_id"):
            continue
        quote = "空列表返回零" if qid == parent else "我负责组内优势计算"
        source = sorted(children)[0] if qid == parent else qid
        value = {"scores": {k: 3 for k in q["rubric"]["dimensions"]}, "evidence_quote": quote,
            "evidence": f"来源 {source}：这是合成测试的脚本评分，仅验证来源与权重，不代表模型能力。",
            "confidence": "medium", "fatal_issues": []}
        result = ri.update_finished_grading(service.repo_root, profile, iid, qid, result=value)
    assert set(result["assessments"]) == {"q-001", "q-002", "q-003", parent}
    assert result["result"]["overall_score"] == 50
    assert not result["result"]["unscored"]
    print(json.dumps({"path": "two" if two else "one", "generation_calls_scripted": 2,
        "code_sha_before_after": [digest,result["coding_defence"]["submission_sha256"]],
        "executions": 0, "grading_calls_scripted": 4, "parent": parent, "children": sorted(children)}))


def test_defence_rejected_sources_restart_and_atomic_retry(unified, monkeypatch):
    service, profile = unified
    iid = coding_scene(service, profile)
    service.save_interview_coding_submission(profile, iid, CODE)
    locked = service.lock_interview_code(profile, iid)
    parent = locked["coding_defence"]["parent_question_id"]
    service = type(service)(service.repo_root)
    c = context(service, profile, iid, None)
    good = defence_packet(c)
    for source, quote in (("code:q-001", "total += x"), ("code:"+parent, "total += 99"), (parent, "total += x")):
        bad = deepcopy(good)
        bad["state_update"]["claims"][0]["evidence"] = {"question_id": source, "quote": quote}
        with pytest.raises(ri.RoleInterviewError): commit(service, profile, iid, c, bad)
        assert service.interview_session(profile, iid) == locked
    bad = deepcopy(c)
    bad["request_basis"]["coding_defence"]["submission_sha256"] = "0"*64
    with pytest.raises(ri.RoleInterviewError): commit(service, profile, iid, bad, good)
    original = ri._atomic_write
    def failed(path, content):
        if path.name == "session.json": raise ri.RoleInterviewError("synthetic disk failure")
        original(path, content)
    monkeypatch.setattr(ri, "_atomic_write", failed)
    with pytest.raises(ri.RoleInterviewError): commit(service, profile, iid, c, good)
    monkeypatch.setattr(ri, "_atomic_write", original)
    assert service.interview_session(profile, iid) == locked
    saved = commit(service, profile, iid, c, good)
    assert len(saved["coding_defence"]["question_ids"]) == 1
    with pytest.raises(ri.RoleInterviewError): commit(service, profile, iid, c, good)
    with pytest.raises(Exception): service.save_interview_coding_submission(profile, iid, CODE + "# edited")
    with pytest.raises(ri.RoleInterviewError): service.lock_interview_code(profile, iid)
    with pytest.raises(ri.RoleInterviewError): service.run_interview_code(profile, iid)
    ri.finish_role_interview(service.repo_root, profile, iid, confirm_incomplete=True)
    with pytest.raises(ri.RoleInterviewError): commit(service, profile, iid, c, good)


@pytest.mark.parametrize("remaining", [59, 60, 61])
def test_defence_time_boundary(unified, monkeypatch, remaining):
    from llm_interview_lab import coding_defence, interview_flow
    service, profile = unified
    iid = coding_scene(service, profile)
    monkeypatch.setattr(interview_flow, "candidate_remaining", lambda *a, **k: remaining)
    service.save_interview_coding_submission(profile, iid, CODE)
    locked = service.lock_interview_code(profile, iid)
    reason = coding_defence.should_close(locked, remaining)
    assert bool(reason) == (remaining < 60)
    if remaining < 60:
        assert locked["coding_defence"]["status"] == "closed"
        result = ri.finish_role_interview(service.repo_root, profile, iid, confirm_incomplete=True)
        assert result["coding_defence"]["question_ids"] == []
        for q in result["questions"]:
            value={"scores":{k:3 for k in q["rubric"]["dimensions"]},"evidence_quote":"total += x" if q["kind"]=="coding" else "我负责组内优势计算",
                "evidence":"来源 code:q-004：仅按现有代码和已保存回答评估；没有答辩不增加零分项。", "confidence":"medium","fatal_issues":[]}
            result=ri.update_finished_grading(service.repo_root,profile,iid,q["question_id"],result=value)
        assert result["result"]["overall_score"]==50 and len(result["assessments"])==4
        print("time_skip generation_calls=0 executions=0 grading_calls_scripted=4 overall=50")


def test_old_protocol3_without_marker_stays_legacy(unified):
    service, profile = unified
    session = service.create_dynamic_interview(profile, role_id="post_training_engineer", difficulty="hard",
        ai_mode="provider", initial_question={"kind":"oral","title":"旧协议","prompt":"请介绍你在合成实验中的具体工作。"},
        context_sha256="a"*64, coding_defence=False)
    assert "coding_defence_version" not in session
    assert service.interview_session(profile, session["interview_id"])["plan_fingerprint"] == session["plan_fingerprint"]


def test_versioned_run_sources_and_final_wire_budget(unified, monkeypatch):
    from llm_interview_lab import coding_defence, interviewer_state
    from llm_interview_lab.ai.interview_context_budget import enforce_wire_budget
    from llm_interview_lab.ai.context_builder import ContextBuilderError
    service, profile = unified
    iid = coding_scene(service, profile)
    # Producer double represents an already-saved older run, not actual execution.
    old_run={"status":"completed","exit_code":0,"stdout":"synthetic prior output","stderr":"",
        "submission_sha256":"9"*64,"question_id":"q-004","recorded_at":"2026-09-10T00:00:00Z"}
    monkeypatch.setattr(ri,"role_coding_run",lambda *a: old_run)
    long_code=CODE + "# 公开合成注释，不是执行指令。\n"*600
    service.save_interview_coding_submission(profile,iid,long_code)
    locked=service.lock_interview_code(profile,iid)
    preview=build_role_interview_context_preview(service.repo_root,profile,iid,include_materials=False,catalog=service.catalog,role_catalog=service.roles)
    c=json.loads(next(p.content for p in preview.parts if p.id=="interview_contract"))
    registry=json.loads(next(p.content for p in preview.parts if p.id=="coding_sources"))
    assert registry[0]["text"]==long_code
    assert registry[1]["matches_locked_code"] is False
    instruction=interviewer_state.instruction()
    provider=enforce_wire_budget(json.dumps([{"role":"system","content":preview.selected_text},{"role":"user","content":instruction}],ensure_ascii=False))
    codex=enforce_wire_budget(json.dumps({"prompt":preview.selected_text+"\n"+instruction,"output_schema":interviewer_state.response_schema(c["loaded_method_ids"])},ensure_ascii=False))
    print("long_defence_final_payload",json.dumps({"provider":provider,"codex":codex,"code_sha":registry[0]["sha256"]}))
    saved=commit(service,profile,iid,c,defence_packet(c))
    qid=saved["questions"][-1]["question_id"]
    answer="口头改法不是已执行结果。"*3000
    service.answer_interview(profile,iid,qid,answer)
    with pytest.raises(ContextBuilderError,match="预算"):
        build_role_interview_context_preview(service.repo_root,profile,iid,include_materials=False,catalog=service.catalog,role_catalog=service.roles)
    assert service.interview_answer_text(profile,iid,qid)==answer
    assert service.interview_session(profile,iid)["coding_defence"]["submission_sha256"]==locked["coding_defence"]["submission_sha256"]


CE_CORE = '''import torch
def cross_entropy(logits, targets, reduction="mean", ignore_index=-100):
    valid = targets != ignore_index
    indices = targets.masked_fill(~valid, 0)
    norm = torch.logsumexp(logits, dim=-1)
    losses = norm - logits.gather(1, indices[:, None]).squeeze(1)
    losses = losses.masked_fill(~valid, 0)
    if reduction == "none":
        return losses
    if reduction == "sum":
        return losses.sum()
    return losses.sum() / valid.sum().clamp_min(1)
'''


@pytest.mark.parametrize("submission", [CE_CORE, CE_CORE.replace("valid.sum().clamp_min(1)", "logits.shape[0]"),
    'import torch\ndef cross_entropy(logits, targets, reduction="mean", ignore_index=-100):\n    norm = torch.logsumexp(logits, dim=-1)\n    losses =\n'])
def test_actual_fixed_task_partial_and_implementation_sources(unified, submission):
    service, profile = unified
    iid=coding_scene(service,profile,problem_id="LOSS-014")
    service.save_interview_coding_submission(profile,iid,submission)
    locked=service.lock_interview_code(profile,iid)
    preview=build_role_interview_context_preview(service.repo_root,profile,iid,include_materials=False,catalog=service.catalog,role_catalog=service.roles)
    parts={p.id:p.content for p in preview.parts}
    c=json.loads(parts["interview_contract"])
    assert "coding_review" in parts and "cross_entropy" in parts["parent_task"]
    value=defence_packet(c)
    value["follow_up"]="这里按最后一维计算 norm，这个中间量是什么形状，与你接下来选择目标类的操作如何对应？"
    value["state_update"]["claims"][0].update(statement="候选人使用最后一维归约，形状衔接待解释",
        evidence={"question_id":"code:q-004","quote":"norm = torch.logsumexp(logits, dim=-1)"})
    saved=commit(service,profile,iid,c,value)
    assert saved["coding_defence"]["submission_sha256"]==hashlib.sha256(submission.encode()).hexdigest()
    assert not saved["coding_evidence"]
    print("fixed_task=LOSS-014 executable_assets=verified actual_executions=0 syntax_not_required_for_defence",
          saved["coding_defence"]["submission_sha256"])


def test_defence_wait_pause_and_resume_share_session_clock(unified):
    from llm_interview_lab.interview_flow import candidate_remaining
    service, profile=unified
    iid=coding_scene(service,profile)
    service.save_interview_coding_submission(profile,iid,CODE)
    locked=service.lock_interview_code(profile,iid)
    start=datetime.fromisoformat(locked["started_at"].replace("Z","+00:00"))+timedelta(minutes=44)
    waiting=ri.set_role_ai_wait(service.repo_root,profile,iid,True,now=start)
    c=context(service,profile,iid,None)
    remaining=candidate_remaining(waiting,start)
    assert candidate_remaining(waiting,start+timedelta(seconds=15))==remaining
    paused=ri.pause_role_interview(service.repo_root,profile,iid,now=start+timedelta(seconds=15))
    assert candidate_remaining(paused,start+timedelta(seconds=30))==remaining
    resumed=ri.resume_role_interview(service.repo_root,profile,iid,now=start+timedelta(seconds=45))
    assert candidate_remaining(resumed,start+timedelta(seconds=45))==remaining
    assert resumed["coding_defence"]["submission_sha256"]==locked["coding_defence"]["submission_sha256"]
    with pytest.raises(ri.RoleInterviewError):
        commit(service,profile,iid,c,defence_packet(c))
