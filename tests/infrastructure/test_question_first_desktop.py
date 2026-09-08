"""Real controller and QML paths; only remote transports use explicit doubles."""
import asyncio
import json
import time
from types import SimpleNamespace

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest
from llm_interview_lab.ai.base import ChatEvent
from llm_interview_lab.ai.codex_backend import CodexEvent
from tests.infrastructure.test_interview_input_runtime import qapp, public_repo, controller, scene, _find
from tests.infrastructure.test_question_first_interview import decision


def wait_until(condition, seconds=8):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QTest.qWait(10)
        time.sleep(.005)
        if condition():
            return
    assert condition()


def provider_scene(controller):
    assert controller.saveConnection("selected", "ollama", "synthetic-model", "合成传输", "http://127.0.0.1:11434", "", "high")
    controller.finishInterview()
    preview = controller.previewInterviewSettings("post_training_engineer", "hard", "", False)
    controller.startConfiguredInterview("post_training_engineer", "hard", "selected", "", False, preview["context_sha256"])
    return controller.interview["interview_id"]


def test_one_submit_streams_next_and_finish_grades_once(scene, monkeypatch):
    window, controller = scene
    iid = provider_scene(controller)
    requests, configs = [], []
    session = controller.service.interview_session(controller.profileId, iid)
    response = decision(controller.service, session, "experience")
    class Provider:
        async def stream_chat(self, messages, **kwargs):
            requests.append(messages)
            if "evidence_quote" in messages[-1]["content"]:
                first = controller.service.interview_session(controller.profileId, iid)["questions"][0]
                value = {"scores": {d: 3 for d in first["rubric"]["dimensions"]},
                         "evidence": "候选人描述独立评测，尚缺如何隔离数据的具体实现证据。", "evidence_quote": "独立评测集",
                         "confidence": "medium", "fatal_issues": [], "follow_up": ""}
                yield ChatEvent("delta", text=json.dumps(value, ensure_ascii=False))
            else:
                raw = json.dumps(response, ensure_ascii=False)
                for index in range(0, len(raw), 12):
                    yield ChatEvent("delta", text=raw[index:index + 12])
                    await asyncio.sleep(.01)
    def factory(config, **kwargs):
        configs.append(config)
        return Provider()
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", factory)
    assert controller.submitInterviewAnswer("我使用独立评测集验证算法，评测数据未用于训练。", "selected", False)
    wait_until(lambda: bool(controller.interview.get("next_question_preview")))
    preview = _find(window, "interviewStreamingQuestion")
    assert "{" not in preview.property("text") and "scores" not in preview.property("text")
    assert controller.interview["answer_locked"]
    wait_until(lambda: not controller.busy)
    assert controller.interview["question"]["question_id"] == "q-002", controller.interview.get("ai_error")
    session = controller.service.interview_session(controller.profileId, iid)
    assert not session["assessments"] and session["ai_wait_seconds"] > 0
    assert len(requests) == 1 and configs[0].reasoning_effort == "high"
    controller.finishInterview()
    assert len(controller.interview["dialogue"]) == 1
    wait_until(lambda: controller.interview.get("result", {}).get("question_scores", {}).get("q-001") is not None)
    wait_until(lambda: not controller.busy)
    assert len(requests) == 2
    controller._load_interview(iid)
    QTest.qWait(100)
    controller.retryInterviewGrading()
    QTest.qWait(100)
    assert len(requests) == 2


def test_provider_cancel_preserves_answer_and_releases_clock(controller, monkeypatch):
    iid = provider_scene(controller)
    class Provider:
        async def stream_chat(self, *args, **kwargs):
            await asyncio.sleep(30)
            yield ChatEvent("delta", text="not reached")
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **kw: Provider())
    assert controller.submitInterviewAnswer("合成回答：我负责本地实验，没有上传真实材料。", "selected", False)
    wait_until(lambda: bool(getattr(controller, "_provider_interview_task", None)))
    controller.stopInterviewGeneration()
    wait_until(lambda: not controller.busy)
    session = controller.service.interview_session(controller.profileId, iid)
    assert "q-001" in session["answers"] and not session["assessments"]
    assert "ai_wait_started_at" not in session
    assert controller.interview["ai_error"]


def test_codex_reuses_transport_for_question_then_end_grading(controller):
    calls, threads = [], []
    async def start_thread(**kwargs):
        threads.append(kwargs)
        return {"thread": {"id": "synthetic-thread"}}
    async def start_turn(*args, **kwargs):
        calls.append((args, kwargs))
        return {"turn": {"id": "synthetic-turn"}}
    controller._codex_backend = SimpleNamespace(start_thread=start_thread, start_turn=start_turn)
    controller._codex_thread_id = "connected"
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    controller._ensure_codex_loop()
    iid = controller.interview["interview_id"]
    assert controller.submitInterviewAnswer("我使用独立评测集验证合成实验。", "codex", False)
    wait_until(lambda: controller._codex_interview_turn_id == "synthetic-turn")
    session = controller.service.interview_session(controller.profileId, iid)
    response = decision(controller.service, session, "experience")
    controller._handle_codex_event(CodexEvent("item/agentMessage/delta", {"turnId": "synthetic-turn", "delta": json.dumps(response, ensure_ascii=False)}))
    assert controller.interview["next_question_preview"] == response["follow_up"]
    controller._handle_codex_event(CodexEvent("turn/completed", {"turnId": "synthetic-turn", "status": "completed"}))
    assert controller.interview["question"]["question_id"] == "q-002", controller.interview.get("ai_error")
    assert "scores" not in calls[0][1]["output_schema"]["properties"]
    controller.finishInterview()
    wait_until(lambda: len(calls) == 2)
    assert len(threads) == 1
    first = session["questions"][0]
    result = {"scores": {d: 3 for d in first["rubric"]["dimensions"]},
              "evidence": "回答指出独立评测，仍缺少具体划分与泄漏排查证据。", "evidence_quote": "独立评测集",
              "confidence": "medium", "fatal_issues": [], "follow_up": ""}
    controller._codex_interview_buffer = json.dumps(result, ensure_ascii=False)
    controller._finish_codex_interview_assessment(controller._codex_interview_identity)
    QCoreApplication.processEvents()
    assert controller.interview["result"]["question_scores"]["q-001"] == 50
    assert not controller.busy


def test_end_grading_restart_skips_success_and_retries_only_failure(controller, tmp_path, monkeypatch):
    from llm_interview_lab.desktop.controller import AppController
    from llm_interview_lab.role_interviews import configure_interview_grading
    iid = provider_scene(controller)
    service, profile = controller.service, controller.profileId
    service.answer_interview(profile, iid, "q-001", "我使用独立评测集验证方法。")
    service.advance_dynamic_interview(profile, iid, "q-001", decision(service, service.interview_session(profile, iid), "experience"), context_sha256="a" * 64)
    service.answer_interview(profile, iid, "q-002", "我使用独立评测集检查重复数据。")
    configure_interview_grading(controller.repo_root, profile, iid, connection_id="selected", include_materials=False)
    controller._load_interview(iid)
    calls = []
    class Provider:
        async def stream_chat(self, messages, **kwargs):
            qid = "q-002" if "question_id=q-002" in messages[0]["content"] else "q-001"
            calls.append(qid)
            if calls == ["q-001"]:
                raise RuntimeError("synthetic timeout; 请重试该题评分")
            q = next(q for q in service.interview_session(profile, iid)["questions"] if q["question_id"] == qid)
            result = {"scores": {d: 3 for d in q["rubric"]["dimensions"]}, "evidence": "回答说明了独立评测和隔离验证，但尚缺具体划分以及排查数据泄漏的实现细节。",
                      "evidence_quote": "独立评测集", "confidence": "medium", "fatal_issues": [], "follow_up": ""}
            yield ChatEvent("delta", text=json.dumps(result, ensure_ascii=False))
    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider", lambda *a, **kw: Provider())
    controller.finishInterview()
    wait_until(lambda: not controller.busy and len(calls) == 2)
    session = service.interview_session(profile, iid)
    assert session["grading"]["questions"]["q-001"]["status"] == "failed"
    assert "q-002" in session["assessments"], (calls, session["grading"])
    controller.shutdown()
    restored = AppController(controller.repo_root, profile_id=profile, log_root=tmp_path / "restored-logs")
    try:
        restored._load_interview(iid)
        QTest.qWait(100)
        assert calls == ["q-001", "q-002"]
        restored.retryInterviewQuestionGrading("q-001")
        wait_until(lambda: not restored.busy and len(calls) == 3)
        assert calls == ["q-001", "q-002", "q-001"]
        assert len(service.interview_session(profile, iid)["assessments"]) == 2
    finally:
        restored.shutdown()


def test_grading_rescope_requires_preview_and_explicit_confirmation(controller, monkeypatch):
    from llm_interview_lab.role_interviews import configure_interview_grading
    iid = provider_scene(controller)
    controller.service.answer_interview(controller.profileId, iid, "q-001", "我完成了合成实验。")
    configure_interview_grading(controller.repo_root, controller.profileId, iid, connection_id="selected", include_materials=False)
    controller._settings.remove(controller._interview_consent_key(iid))
    calls = []
    monkeypatch.setattr(controller, "assessInterviewWithProvider", lambda *a, **kw: calls.append(kw))
    controller.finishInterview()
    QTest.qWait(50)
    assert not calls
    preview = controller.previewInterviewGrading()
    assert preview["parts"] and preview["scope_sha256"]
    assert not controller.authorizeInterviewGrading("stale") and not calls
    assert controller.authorizeInterviewGrading(preview["scope_sha256"])
    assert len(calls) == 1


def test_fresh_profile_and_last_choices_survive_restart_without_hidden_stage(controller, tmp_path):
    from llm_interview_lab.desktop.controller import AppController
    from llm_interview_lab.workspace import load_profile, profile_paths
    assert controller.createLearningProfile("统一难度中文测试", "ai_algorithm_research_engineer")
    profile = controller.profileId
    saved = load_profile(profile_paths(controller.repo_root, profile), controller.repo_root)
    assert "seniority" not in saved["role_preferences"]
    assert controller.interviewPreferences()["difficulty"] == "medium"
    assert controller.interviewPreferences()["duration_minutes"] == "60"
    controller.saveInterviewPreferences({"difficulty": "hard", "duration_minutes": "45", "ai_mode": "provider", "connection_id": "selected"})
    controller.shutdown()
    restored = AppController(controller.repo_root, log_root=tmp_path / "fresh-restart")
    try:
        assert restored.profileId == profile and not restored.onboardingRequired
        assert restored.interviewPreferences()["difficulty"] == "hard"
        assert restored.interviewPreferences()["duration_minutes"] == "45"
        assert restored.interviewPreferences()["connection_id"] == "selected"
        assert "seniority" not in restored.interviewPreferences()
    finally:
        restored.shutdown()
