"""Protocol 3 through production QML/Controller; no remote services."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest
from PySide6.QtGui import QInputMethodEvent

from llm_interview_lab.ai.base import ChatEvent
from llm_interview_lab.ai.codex_backend import CodexEvent
from tests.infrastructure.test_interview_input_runtime import qapp, public_repo, controller, scene, _find, _click, _visible_hints
from tests.infrastructure.test_question_first_desktop import wait_until, provider_scene
from tests.infrastructure.test_interviewer_evidence import packet


@pytest.mark.parametrize("controller", [3], indirect=True)
def test_cancel_retry_late_and_duplicate_callbacks(controller, monkeypatch):
    app = controller
    iid = provider_scene(app)
    pending = []
    class Provider:
        async def stream_chat(self, messages, **kwargs):
            contract = json.JSONDecoder().raw_decode(messages[0]["content"].split(
                "## 本轮证据、缺口、岗位范围与决策协议\n", 1)[1])[0]
            gate = asyncio.Event()
            pending.append((asyncio.get_running_loop(), gate, packet(contract)))
            # Simulate a transport that delivers a response despite cancellation.
            try:
                await gate.wait()
            except asyncio.CancelledError:
                await gate.wait()
            yield ChatEvent("delta", text=json.dumps(packet(contract), ensure_ascii=False))
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **k: Provider())
    answer = "我负责组内优势计算。"
    assert app.submitInterviewAnswer(answer, "selected", False)
    wait_until(lambda: len(pending) == 1)
    worker_a = next(iter(app._workers))
    app.stopInterviewGeneration()
    assert not app.busy
    assert app.submitInterviewAnswer(answer, "selected", False)
    wait_until(lambda: len(pending) == 2)
    worker_b = next(w for w in app._workers if w is not worker_a)
    operation_b = app._interview_provider_operation_id
    # Late error and progress from A cannot clear B's wait or current UI.
    worker_a.signals.failed.emit("late synthetic A")
    assert app._interview_provider_operation_id == operation_b and app.busy
    assert "ai_wait_started_at" in app.service.interview_session(app.profileId, iid)
    pending[1][0].call_soon_threadsafe(pending[1][1].set)
    wait_until(lambda: app.interview["question"]["question_id"] == "q-002")
    saved = app.service.interview_session(app.profileId, iid)
    worker_b.signals.completed.emit(pending[1][2])
    pending[0][0].call_soon_threadsafe(pending[0][1].set)
    wait_until(lambda: pending[0][0].is_closed())
    QCoreApplication.processEvents()
    assert app.service.interview_session(app.profileId, iid) == saved
    assert saved["interviewer_state"]["revision"] == 1
    assert not app.busy and not app.interview.get("ai_error")


def captured_contract(preview):
    return json.loads(next(p.content for p in preview.parts if p.id == "interview_contract"))


@pytest.mark.parametrize("controller", [3], indirect=True)
def test_actual_provider_codex_business_equivalence_and_late_codex(controller, monkeypatch):
    app = controller
    iid = provider_scene(app)
    messages, turns = [], []
    class Provider:
        async def stream_chat(self, request, **kwargs):
            messages.append(request)
            yield ChatEvent("delta", text="{}")  # Keep the same locked answer for Codex retry.
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **k: Provider())
    answer = "我负责组内优势计算，GRPO还需要核对零方差行为。"
    assert app.submitInterviewAnswer(answer, "selected", False)
    wait_until(lambda: not app.busy)
    async def start_thread(**kwargs):
        return {"thread": {"id": "equivalence-thread"}}
    async def start_turn(*args, **kwargs):
        turns.append((args, kwargs))
        return {"turn": {"id": f"equivalence-{len(turns)}"}}
    async def interrupt(*args):
        return {}
    app._codex_backend = SimpleNamespace(start_thread=start_thread, start_turn=start_turn, interrupt=interrupt)
    app._codex_thread_id = "connected"
    app._codex_thread_mode = "interviewer"
    app._codex_pump_started = True
    app._ensure_codex_loop()
    # Same locked synthetic input through the two public transport slots;
    # this is not a claim that a frozen session can switch provider in the UI.
    from llm_interview_lab.role_interviews import set_role_ai_wait
    set_role_ai_wait(app.repo_root, app.profileId, iid, True)
    assert app.interviewContextPreview(answer, False)["parts"]
    assert app.sendCodexInterviewAnswer(answer, False)
    wait_until(lambda: app._codex_interview_turn_id == "equivalence-1")
    actual_prompt = turns[0][0][1]
    assert turns[0][1]["model"] == (app._codex_model or None)
    assert turns[0][1]["effort"] == (app._codex_reasoning_effort or None)
    codex_business, codex_instruction = actual_prompt.split("\n\n## Frozen scorecard contract\n", 1)
    assert messages[0][1]["content"] == codex_instruction
    def normalized(body):
        prefix, rest = body.split("## 本轮证据、缺口、岗位范围与决策协议\n", 1)
        contract, end = json.JSONDecoder().raw_decode(rest)
        contract.pop("remaining_seconds_at_turn_start")  # only wall-time snapshot differs across sequential sends
        return prefix, contract, rest[end:]
    assert normalized(messages[0][0]["content"]) == normalized(codex_business)
    old_value = packet(captured_contract(app._codex_interview_request_preview))
    app.cancelCodex()
    app._handle_codex_event(CodexEvent("turn/completed", {"turnId": "equivalence-1", "status": "interrupted"}))
    assert not app.busy
    set_role_ai_wait(app.repo_root, app.profileId, iid, True)
    assert app.interviewContextPreview(answer, False)["parts"]
    assert app.sendCodexInterviewAnswer(answer, False)
    wait_until(lambda: app._codex_interview_turn_id == "equivalence-2")
    c = captured_contract(app._codex_interview_request_preview)
    app._handle_codex_event(CodexEvent("item/agentMessage/delta", {"turnId": "equivalence-1", "delta": json.dumps(old_value)}))
    app._handle_codex_event(CodexEvent("turn/completed", {"turnId": "equivalence-1", "status": "completed"}))
    assert app.busy and app._codex_interview_turn_id == "equivalence-2"
    raw = json.dumps(packet(c), ensure_ascii=False)
    app._handle_codex_event(CodexEvent("item/agentMessage/delta", {"turnId": "equivalence-2", "delta": raw}))
    app._handle_codex_event(CodexEvent("turn/completed", {"turnId": "equivalence-2", "status": "completed"}))
    saved = app.service.interview_session(app.profileId, iid)
    app._handle_codex_event(CodexEvent("turn/completed", {"turnId": "equivalence-2", "status": "completed"}))
    assert app.service.interview_session(app.profileId, iid) == saved
    assert saved["interviewer_state"]["revision"] == 1
    assert len(messages) == 1 and len(turns) == 2


@pytest.mark.parametrize("controller", [3], indirect=True)
@pytest.mark.parametrize("failure_mode", ["quote", "storage"])
def test_provider_buffer_rejection_retry_and_visible_history(scene, monkeypatch, failure_mode):
    window, app = scene
    iid = provider_scene(app)
    requests, previews = [], []
    fail = [True]
    if failure_mode == "storage":
        import llm_interview_lab.role_interviews as domain
        atomic_write = domain._atomic_write
        def write(path, content):
            if path.name == "session.json" and fail[0] and json.loads(content).get("interviewer_state", {}).get("revision") == 1:
                raise domain.RoleInterviewError("synthetic storage failure")
            return atomic_write(path, content)
        monkeypatch.setattr(domain, "_atomic_write", write)
    class Provider:
        async def stream_chat(self, messages, **kwargs):
            requests.append(messages)
            # Read the exact captured request, not mutable Controller state.
            raw_contract = messages[0]["content"].split("## 本轮证据、缺口、岗位范围与决策协议\n", 1)[1]
            contract = json.JSONDecoder().raw_decode(raw_contract)[0]
            value = packet(contract)
            if fail[0] and failure_mode == "quote":
                value["state_update"]["claims"][0]["evidence"]["quote"] = "不存在的证据"
            # Put display text FIRST: key order must never bypass validation.
            raw = json.dumps(value, ensure_ascii=False)
            for i in range(0, len(raw), 150):
                yield ChatEvent("delta", text=raw[i:i + 150])
                previews.append(app.interview.get("next_question_preview", ""))
                await asyncio.sleep(.003)
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **k: Provider())
    answer = "我负责组内优势计算，使用组内均值作为基线。"
    assert app.submitInterviewAnswer(answer, "selected", False)
    wait_until(lambda: not app.busy)
    assert len(requests) == 1 and not any(previews)
    assert app.interview["question"]["question_id"] == "q-001"
    assert app.interview["answer_locked"] and app.interview["ai_error"]
    assert app.service.interview_session(app.profileId, iid)["interviewer_state"]["revision"] == 0
    fail[0] = False
    # Retry through the real QML button, without another consent/continue step.
    _click(window, _find(window, "lockInterviewAnswer"))
    wait_until(lambda: not app.busy)
    assert len(requests) == 2
    assert app.interview["question"]["question_id"] == "q-002", app.interview["ai_error"]
    assert app.service.interview_session(app.profileId, iid)["interviewer_state"]["revision"] == 1
    assert app.interview["dialogue"][0]["answer"] == answer
    assert _find(window, "interviewConversation").isVisible()
    editor = _find(window, "interviewAnswerEditor")
    editor.forceActiveFocus()
    preedit = QInputMethodEvent("组内均值", [])
    QCoreApplication.sendEvent(editor, preedit)
    assert not _visible_hints(editor)
    committed = QInputMethodEvent()
    committed.setCommitString("组内均值作为基线。")
    QCoreApplication.sendEvent(editor, committed)
    assert "组内均值" in editor.property("text")
    assert app.interview["decision_validation_ms"] >= 0
    print("provider_mock_validation_ms", app.interview["decision_validation_ms"])


@pytest.mark.parametrize("controller", [3], indirect=True)
def test_codex_same_contract_no_partial_question_and_reused_thread(controller):
    app = controller
    calls, threads = [], []
    async def start_thread(**kwargs):
        threads.append(kwargs)
        return {"thread": {"id": "synthetic-evidence-thread"}}
    async def start_turn(*args, **kwargs):
        calls.append((args, kwargs))
        return {"turn": {"id": f"evidence-turn-{len(calls)}"}}
    app._codex_backend = SimpleNamespace(start_thread=start_thread, start_turn=start_turn)
    app._codex_thread_id = "connected"
    app._codex_thread_mode = "interviewer"
    app._codex_pump_started = True
    app._ensure_codex_loop()
    for index in range(2):
        assert app.submitInterviewAnswer("我负责组内优势计算，还需要核对实现细节。", "codex", False)
        turn_id = f"evidence-turn-{index + 1}"
        wait_until(lambda: app._codex_interview_turn_id == turn_id)
        contract = captured_contract(app._codex_interview_request_preview)
        value = packet(contract, intro=index == 0, experience_ref="new:exp" if index == 0 else "exp-0001")
        raw = json.dumps(value, ensure_ascii=False)
        app._handle_codex_event(CodexEvent("item/agentMessage/delta", {"turnId": turn_id, "delta": raw}))
        assert not app.interview["next_question_preview"]
        app._handle_codex_event(CodexEvent("turn/completed", {"turnId": turn_id, "status": "completed"}))
        assert app.interview["question"]["question_id"] == f"q-{index + 2:03d}", app.interview["ai_error"]
    assert len(threads) == 1 and len(calls) == 2
    assert "state_update" in calls[0][1]["output_schema"]["properties"]
    assert "scores" not in calls[0][1]["output_schema"]["properties"]
    assert not app.busy


@pytest.mark.parametrize("controller", [3], indirect=True)
def test_cancel_late_provider_result_keeps_locked_answer(controller, monkeypatch):
    app = controller
    iid = provider_scene(app)
    started = []
    class Provider:
        async def stream_chat(self, messages, **kwargs):
            started.append(True)
            await asyncio.sleep(10)
            yield ChatEvent("delta", text="{}")
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **k: Provider())
    assert app.submitInterviewAnswer("我负责组内优势计算。", "selected", False)
    wait_until(lambda: started)
    app.stopInterviewGeneration()
    wait_until(lambda: not app.busy)
    state = app.service.interview_session(app.profileId, iid)
    assert state["interviewer_state"]["revision"] == 0
    assert "q-001" in state["answers"] and len(state["questions"]) == 1
    assert "ai_wait_started_at" not in state
