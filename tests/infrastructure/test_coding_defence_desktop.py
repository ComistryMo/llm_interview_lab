"""Formal desktop chain; only inference and the clock are controlled doubles."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest
from tests.infrastructure.test_interview_input_runtime import qapp, public_repo, controller, scene, _find
from tests.infrastructure.test_question_first_desktop import provider_scene, wait_until
from tests.infrastructure.test_interviewer_evidence import packet
from tests.infrastructure.test_coding_defence import CODE, defence_packet
from llm_interview_lab.ai.base import ChatEvent
from llm_interview_lab.ai.codex_backend import CodexEvent


def preserve_trace(name, trace, session):
    """Opt-in synthetic artifacts only; never exports a Profile directory."""
    destination=os.environ.get("LLM_LAB_EVIDENCE_ARTIFACT_ROOT")
    if not destination:
        return
    root=Path(destination).resolve()
    assert root.is_relative_to(Path(__file__).resolve().parents[2]/"workspace"/"maintainer")
    root.mkdir(parents=True,exist_ok=True)
    content=json.dumps({"synthetic_only":True,"transport":"Fake","semantic_quality":"UNRUN",
        "exchanges":trace,"defence":session["coding_defence"],"grading":session["grading"],
        "question_weights":{q["question_id"]:q["round_weight"] for q in session["questions"] if not q.get("parent_coding_question_id")},
        "assessments":session["assessments"],"execution_calls":0},ensure_ascii=False,indent=2).encode()
    (root/(name+".json")).write_bytes(content)
    (root/(name+".manifest.json")).write_text(json.dumps({"file":name+".json","sha256":hashlib.sha256(content).hexdigest(),
        "baseline_sha":"b954c71d6a7029010fc247cbf7eef6c880a102f1","synthetic_only":True}),encoding="utf-8")


@pytest.mark.parametrize("controller", [3], indirect=True)
@pytest.mark.parametrize("transport", ["provider", "provider_retry", "provider_two", "codex", "codex_end", "codex_no_ack"])
def test_formal_coding_defence_whole_chain(scene, monkeypatch, transport):
    window, app = scene
    iid = provider_scene(app) if transport.startswith("provider") else app.interview["interview_id"]
    connection = "selected" if transport.startswith("provider") else "codex"
    clock = [3600]
    monkeypatch.setattr("llm_interview_lab.interview_flow.candidate_remaining", lambda *a, **k: clock[0])
    generation, grading, queued, trace = [], [], [], []
    def response(body):
        if app._interview_grading_identity:
            qid = app._interview_grading_identity[2]
            session = app.service.interview_session(app.profileId, iid)
            q = next(q for q in session["questions"] if q["question_id"] == qid)
            grading.append(qid)
            return {"scores": {k: 3 for k in q["rubric"]["dimensions"]},
                "evidence_quote": ("total += x" if transport=="codex_end" else "空列表返回零") if q["kind"] == "coding" else "我负责组内优势计算",
                "evidence": "来源 code:q-004 / q-005：本测试只验证真实来源和队列，不声称模型已经判断实现正确。",
                "confidence": "medium", "fatal_issues": [], "follow_up": ""}
        c = json.JSONDecoder().raw_decode(body.split("## 本轮证据、缺口、岗位范围与决策协议\n", 1)[1])[0]
        generation.append(c)
        if "coding_defence" in c:
            value = defence_packet(c, first=not c["coding_defence"]["question_ids"], finish=bool(c["coding_defence"]["question_ids"]) and transport!="provider_two")
            if transport=="provider_retry" and len(generation)==4:
                value["state_update"]["claims"][0]["evidence"]["quote"]="total += fabricated"
            return value
        index = len(generation)-1
        value = packet(c, intro=index==0, claim_ref="new:claim" if index==0 else "claim-0001", experience_ref="new:exp" if index==0 else "exp-0001")
        if index:
            value.update(next_stage="theory" if index==1 else "coding", transition_reason="time_deferred")
            value["probe"]["action"] = "transition"
        if index==2:
            value.update(follow_up="", next_skill_ids=[], coding_problem_id=c["coding_candidates"][0]["id"])
        return value
    class Provider:
        async def stream_chat(self, messages, **kw):
            value=response(messages[0]["content"])
            trace.append({"request":messages,"response":value})
            yield ChatEvent("delta", text=json.dumps(value, ensure_ascii=False))
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **kw: Provider())
    async def start_thread(**kw): return {"thread":{"id":"defence-thread"}}
    async def start_turn(*args, **kw):
        queued.append((args, kw))
        return {"turn":{"id": f"defence-turn-{len(queued)}"}}
    async def interrupt(*args): return {}
    closed = []
    async def close(): closed.append(True)
    if transport.startswith("codex"):
        app._codex_backend = SimpleNamespace(start_thread=start_thread, start_turn=start_turn,interrupt=interrupt,close=close)
        app._codex_thread_id="connected"; app._codex_thread_mode="interviewer"; app._codex_pump_started=True
        app._ensure_codex_loop()
    delivered = [0]
    def deliver():
        if not transport.startswith("codex"): return
        wait_until(lambda: len(queued)>delivered[0] and app._codex_interview_turn_id == f"defence-turn-{delivered[0]+1}", seconds=40)
        args, kw = queued[delivered[0]]
        assert kw["model"] == (app._codex_model or None)
        assert kw["effort"] == (app._codex_reasoning_effort or None)
        turn_id=app._codex_interview_turn_id
        raw=json.dumps(response(args[1]), ensure_ascii=False)
        trace.append({"request":{"prompt":args[1],**kw},"response":json.loads(raw)})
        delivered[0]+=1
        app._handle_codex_event(CodexEvent("item/agentMessage/delta", {"turnId":turn_id,"delta":raw}))
        app._handle_codex_event(CodexEvent("turn/completed", {"turnId":turn_id,"status":"completed"}))
    for remaining in (3600,1800,900):
        clock[0]=remaining
        qid=app.interview["question"]["question_id"]
        assert app.submitInterviewAnswer("我负责组内优势计算。", connection, False)
        deliver()
        wait_until(lambda: not app.busy, seconds=40)
        assert app.interview["question"]["question_id"] != qid, app.interview.get("ai_error")
    clock[0]=600
    locks=[]
    original_lock=app.service.lock_interview_code
    def lock(*args, **kw):
        locks.append(True)
        return original_lock(*args, **kw)
    monkeypatch.setattr(app.service,"lock_interview_code",lock)
    assert app.submitInterviewCode(CODE, connection, False)
    if transport in ("codex_end", "codex_no_ack"):
        wait_until(lambda:app._codex_interview_turn_id=="defence-turn-4",seconds=40)
        app.finishInterview()
        assert app.interview["status"] in ("completed","incomplete")
        if transport == "codex_no_ack":
            from llm_interview_lab.desktop.controller import AppController
            ended = app.service.interview_session(app.profileId, iid)
            assert app._codex_drain_pending and not app.busy
            assert ended["coding_defence"]["close_reason"] == "user_end"
            assert ended["coding_defence"]["submission_sha256"] == hashlib.sha256(CODE.encode()).hexdigest()
            app._start_pending_grading()
            assert len(queued) == 4 and grading == []
            # Execute the existing timeout callback deterministically, no 5s sleep.
            token = app._codex_drain_token
            app._expire_codex_drain("not-the-owner")
            assert app._codex_drain_pending
            app._expire_codex_drain(token)
            wait_until(lambda: bool(closed), seconds=10)
            assert not app._codex_drain_pending and app._codex_backend is None
            app._start_pending_grading()
            app._handle_codex_event(CodexEvent("turn/completed", {"turnId":"defence-turn-4","status":"completed"}))
            assert app.service.interview_session(app.profileId, iid) == ended
            restored = AppController(app.repo_root, profile_id=app.profileId)
            try:
                assert restored.interview["interview_id"] == iid
                assert restored.interview["status"] in ("completed", "incomplete")
                restored._start_pending_grading()
                restored.finishInterview()
                assert restored.service.interview_session(app.profileId, iid) == ended
                assert set(ended["grading"]["questions"]) == {"q-001", "q-002", "q-003", "q-004"}
                assert len(queued) == 4 and grading == []
                print("codex_no_ack decisions_started=4 displayed_defence=0 closing_only=0 grading=0 executions=0; pending_parent_units=4")
                preserve_trace(transport, trace, ended)
            finally:
                restored.shutdown()
            return
        delivered[0]+=1
        app._handle_codex_event(CodexEvent("item/agentMessage/delta",{"turnId":"defence-turn-4","delta":"不得接纳的晚到数据"}))
        app._handle_codex_event(CodexEvent("turn/completed",{"turnId":"defence-turn-4","status":"interrupted"}))
        for _ in range(4): deliver()
        wait_until(lambda:len(app.service.interview_session(app.profileId,iid)["assessments"])==4,seconds=40)
        ended=app.service.interview_session(app.profileId,iid)
        assert ended["coding_defence"]["close_reason"]=="user_end"
        assert ended["coding_defence"]["question_ids"]==[]
        assert len(queued)==8 and len(grading)==4
        print("codex_end generation_started=4 (last cancelled) grading=4 executions=0 children=0")
        preserve_trace(transport,trace,ended)
        return
    deliver()
    wait_until(lambda: not app.busy, seconds=40)
    if transport=="provider_retry":
        assert app.interview["answer_locked"] and app.interview.get("ai_error")
        before=app.service.interview_session(app.profileId,iid)
        assert before["coding_defence"]["status"]=="pending" and not before["coding_defence"]["question_ids"]
        assert _find(window,"interviewCodingEditor").property("readOnly")
        QMetaObject.invokeMethod(_find(window,"submitInterviewCode"),"clicked",Qt.DirectConnection)
        wait_until(lambda: not app.busy,seconds=40)
        assert app.service.interview_session(app.profileId,iid)["coding_defence"]["submission_sha256"]==before["coding_defence"]["submission_sha256"]
    assert len(locks)==1
    assert app.interview["question"].get("parent_coding_question_id"), app.interview.get("ai_error")
    QCoreApplication.processEvents()
    button=_find(window,"viewDefenceCode")
    QMetaObject.invokeMethod(button,"clicked", Qt.DirectConnection)
    QCoreApplication.processEvents()
    editor=_find(window,"lockedDefenceCode")
    assert editor.property("readOnly") and editor.property("text")==CODE
    oral=_find(window,"interviewAnswerEditor")
    oral.forceActiveFocus()
    QCoreApplication.sendEvent(oral,QInputMethodEvent("中文",[]))
    assert oral.property("preeditText")=="中文"
    event=QInputMethodEvent(); event.setCommitString("空列表返回零。")
    QCoreApplication.sendEvent(oral,event)
    assert "空列表返回零" in oral.property("text")
    assert app.submitInterviewAnswer(oral.property("text"), connection, False)
    deliver()
    if transport=="provider_two":
        wait_until(lambda: not app.busy,seconds=40)
        assert app.interview["question"]["question_id"]=="q-006"
        assert app.submitInterviewAnswer("这里只是口头提出修复，代码没有改动，也没有重新执行。",connection,False)
    wait_until(lambda: app.interview["status"] in ("completed","incomplete"), seconds=40)
    if transport=="codex":
        for _ in range(4): deliver()
    wait_until(lambda: len(app.service.interview_session(app.profileId,iid)["assessments"])==4,seconds=40)
    session=app.service.interview_session(app.profileId,iid)
    assert len(generation)==(6 if transport=="provider_retry" else 5) and len(grading)==4
    assert set(grading)=={"q-001","q-002","q-003","q-004"}
    assert session["result"]["overall_score"]==50 and not session["result"]["unscored"]
    assert session["coding_defence"]["question_ids"]==(["q-005","q-006"] if transport=="provider_two" else ["q-005"])
    if transport=="provider_two":
        assert "q-006" not in session["interviewer_state"]["applied_answers"]
        assert "口头提出修复" in app.service.interview_answer_text(app.profileId,iid,"q-006")
    assert not session["coding_evidence"]
    app.finishInterview(); QCoreApplication.processEvents()
    assert len(grading)==4
    print(transport,f"generation={len(generation)} grading=4 executions=0 locks={len(locks)} children={session['coding_defence']['question_ids']}")
    preserve_trace(transport,trace,session)


@pytest.mark.parametrize("controller", [3], indirect=True)
@pytest.mark.parametrize("end_reason",["user_end","time_deferred"])
def test_defence_cancel_storage_retry_late_duplicate_and_user_end(scene, monkeypatch,end_reason):
    from tests.infrastructure.test_coding_defence import coding_scene
    from llm_interview_lab import role_interviews as ri
    window, app=scene
    provider_scene(app)
    iid=coding_scene(app.service,app.profileId)
    app._load_interview(iid)
    monkeypatch.setattr("llm_interview_lab.interview_flow.candidate_remaining",lambda *a,**k:600)
    app.service.save_interview_coding_submission(app.profileId,iid,CODE)
    app.service.lock_interview_code(app.profileId,iid)
    app._load_interview(iid)
    app.interviewContextPreview(CODE,False)
    assert app.authorizeInterviewConversation(CODE,"selected",False)
    pending=[]
    class Provider:
        async def stream_chat(self,messages,**kw):
            c=json.JSONDecoder().raw_decode(messages[0]["content"].split("## 本轮证据、缺口、岗位范围与决策协议\n",1)[1])[0]
            gate=asyncio.Event()
            pending.append((asyncio.get_running_loop(),gate,defence_packet(c)))
            try: await gate.wait()
            except asyncio.CancelledError: await gate.wait()
            yield ChatEvent("delta",text=json.dumps(defence_packet(c),ensure_ascii=False))
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider",lambda *a,**k:Provider())
    assert app.submitInterviewCode(CODE,"selected",False)
    wait_until(lambda:len(pending)==1,seconds=40)
    worker_a=next(iter(app._workers))
    app.stopInterviewGeneration()
    assert app.submitInterviewCode(CODE,"selected",False)
    wait_until(lambda:len(pending)==2,seconds=40)
    operation_b=app._interview_provider_operation_id
    worker_a.signals.failed.emit("late synthetic A")
    assert app.busy and app._interview_provider_operation_id==operation_b
    original=ri._atomic_write
    def fail_result(path,data):
        if path.name=="session.json" and json.loads(data)["interviewer_state"]["revision"]==4:
            raise ri.RoleInterviewError("synthetic storage failure")
        original(path,data)
    monkeypatch.setattr(ri,"_atomic_write",fail_result)
    pending[1][0].call_soon_threadsafe(pending[1][1].set)
    wait_until(lambda:not app.busy,seconds=40)
    assert app.interview["answer_locked"] and app.interview.get("ai_error")
    assert not app.service.interview_session(app.profileId,iid)["coding_defence"]["question_ids"]
    monkeypatch.setattr(ri,"_atomic_write",original)
    QMetaObject.invokeMethod(_find(window,"submitInterviewCode"),"clicked",Qt.DirectConnection)
    wait_until(lambda:len(pending)==3,seconds=40)
    worker_c=next(w for w in app._workers if w is not worker_a)
    pending[2][0].call_soon_threadsafe(pending[2][1].set)
    wait_until(lambda:not app.busy,seconds=40)
    saved=app.service.interview_session(app.profileId,iid)
    worker_c.signals.completed.emit(pending[2][2])
    pending[0][0].call_soon_threadsafe(pending[0][1].set)
    wait_until(lambda:pending[0][0].is_closed(),seconds=40)
    assert app.service.interview_session(app.profileId,iid)==saved
    assert saved["coding_defence"]["question_ids"]==["q-005"]
    monkeypatch.setattr(app,"_start_pending_grading",lambda *a,**k:None)
    if end_reason=="time_deferred":
        monkeypatch.setattr("llm_interview_lab.interview_flow.candidate_remaining",lambda *a,**k:0)
        app.refreshInterviewClock()
    else:
        app.finishInterview()
    app.finishInterview()
    ended=app.service.interview_session(app.profileId,iid)
    assert ended["coding_defence"]["close_reason"]==end_reason
    assert "q-005" not in ended["grading"]["questions"]
    assert len(pending)==3


@pytest.mark.parametrize("controller", [3], indirect=True)
def test_existing_unmarked_protocol3_still_finishes_on_code(controller,monkeypatch):
    from tests.infrastructure.test_coding_defence import coding_scene
    app=controller
    provider_scene(app)
    iid=coding_scene(app.service,app.profileId,coding_defence=False)
    app._load_interview(iid)
    app.interviewContextPreview(CODE,False)
    assert app.authorizeInterviewConversation(CODE,"selected",False)
    calls=[]
    monkeypatch.setattr(app,"assessInterviewWithProvider",lambda *a,**kw:calls.append(kw))
    assert app.submitInterviewCode(CODE,"selected",False)
    assert app.interview["status"] in ("completed","incomplete")
    QCoreApplication.processEvents()
    assert calls and all(c.get("_grading_question") for c in calls)
    session=app.service.interview_session(app.profileId,iid)
    assert "coding_defence" not in session and "coding_defence_version" not in session


@pytest.mark.parametrize("controller", [3], indirect=True)
@pytest.mark.parametrize("two", [False, True])
def test_restart_after_defence_closed_before_queued_finish(controller, monkeypatch, two):
    """Recreate the durable boundary, without running the old process's finish callback."""
    from llm_interview_lab.desktop.controller import AppController
    from tests.infrastructure.test_coding_defence import coding_scene
    from tests.infrastructure.test_interviewer_evidence import context, commit
    app = controller
    iid = coding_scene(app.service, app.profileId)
    app.service.save_interview_coding_submission(app.profileId, iid, CODE)
    app.service.lock_interview_code(app.profileId, iid)
    c = context(app.service, app.profileId, iid, None)
    commit(app.service, app.profileId, iid, c, defence_packet(c))
    app.service.answer_interview(app.profileId, iid, "q-005", "空列表返回零，但未运行。")
    c = context(app.service, app.profileId, iid, None)
    before = commit(app.service, app.profileId, iid, c, defence_packet(c, first=False, finish=not two))
    final_id = "q-006" if two else "q-005"
    final_text = "这里应该改成其他形式；只是口头建议，没有执行。" if two else "空列表返回零，但未运行。"
    if two:
        before = app.service.answer_interview(app.profileId, iid, final_id, final_text)
    assert before["status"] == "active" and before["coding_defence"]["status"] == "closed"
    # No finish call, no pending timer carried across the process boundary.
    monkeypatch.setattr(AppController, "_start_pending_grading", lambda *a, **kw: None)
    for method in ("sendCodexInterviewAnswer", "assessInterviewWithProvider", "submitInterviewCode"):
        monkeypatch.setattr(AppController, method, lambda *a, **kw: pytest.fail("unexpected generation/relocking on recovery"))
    restored = AppController(app.repo_root, profile_id=app.profileId)
    try:
        QCoreApplication.processEvents()
        assert restored.interview["interview_id"] == iid
        after = restored.service.interview_session(app.profileId, iid)
        assert after["status"] in ("completed", "incomplete")
        assert restored.service.interview_answer_text(app.profileId, iid, final_id) == final_text
        assert after["questions"] == before["questions"] and after["answers"] == before["answers"]
        assert after["interviewer_state"] == before["interviewer_state"]
        assert after["coding_defence"] == before["coding_defence"]
        if two:
            assert final_id not in after["interviewer_state"]["applied_answers"]
        assert set(after["grading"]["questions"]) == {"q-001", "q-002", "q-003", "q-004"}
        restored._load_interview(iid)
        restored.finishInterview()
        assert restored.service.interview_session(app.profileId, iid) == after
        print(f"restart_closed two={two} final={final_id} decisions=0 closing_only=0 grading=0 executions=0 parent_units=4")
        preserve_trace("restart_closed_two" if two else "restart_closed_one", [], after)
    finally:
        restored.shutdown()
