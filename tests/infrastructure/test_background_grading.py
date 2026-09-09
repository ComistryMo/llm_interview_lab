"""Small controller fences for non-blocking end-of-interview grading."""

from __future__ import annotations

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest

from llm_interview_lab.ai.codex_backend import CodexEvent
from llm_interview_lab.ai.base import ChatEvent
from llm_interview_lab.role_interviews import configure_interview_grading
from tests.infrastructure.test_question_first_desktop import provider_scene
from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, _wait_for_asr,
)


def _wait_until(predicate, seconds=5):
    assert _wait_for_asr(predicate, timeout_ms=seconds * 1000)


def _prepare_provider_pending(controller):
    interview_id = provider_scene(controller)
    profile_id = controller.profileId
    service = controller.service
    service.answer_interview(
        profile_id,
        interview_id,
        "q-001",
        "合成答案引用独立测试集并说明边界条件。",
    )
    configure_interview_grading(
        controller.repo_root,
        profile_id,
        interview_id,
        connection_id="selected",
        include_materials=False,
    )
    service.finish_interview(
        profile_id,
        interview_id,
        summary="合成评分测试",
        confirm_incomplete=True,
    )
    controller._load_interview(interview_id)
    key, scope = controller._interview_conversation_consent("selected", False)
    controller._settings.setValue(key, scope)
    controller._start_pending_grading()
    return interview_id


def test_provider_grading_stop_before_provider_initialization(controller, monkeypatch):
    """Stopping during provider construction must not start stream_chat."""

    entered = threading.Event()
    allow_initialization = threading.Event()
    stream_calls = []

    class Provider:
        async def stream_chat(self, *args, **kwargs):
            stream_calls.append(True)
            yield ChatEvent("delta", text="should not be requested")

    def factory(*args, **kwargs):
        entered.set()
        allow_initialization.wait(3)
        return Provider()

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.create_chat_provider", factory
    )
    interview_id = _prepare_provider_pending(controller)
    assert entered.wait(3)
    assert controller.interviewGrading["active"]

    assert controller.stopInterviewGrading()
    allow_initialization.set()
    _wait_until(lambda: not controller._workers)
    assert controller.interviewGrading.get("paused") is True

    assert not stream_calls
    assert not controller.service.interview_session(
        controller.profileId, interview_id
    )["assessments"]


@pytest.mark.parametrize("destination", ["interview", "profile"])
def test_late_provider_grading_after_switch_is_discarded(
    controller, monkeypatch, destination
):
    """A late score from an old interview cannot write the newly opened one."""

    release = threading.Event()
    stream_started = threading.Event()
    old_interview = {}

    class Provider:
        async def stream_chat(self, *args, **kwargs):
            stream_started.set()
            while not release.is_set():
                try:
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    # Simulate a response already in flight when cancelled.
                    continue
            question = old_interview["question"]
            result = {
                "scores": {key: 3 for key in question["rubric"]["dimensions"]},
                "evidence": "回答说明了独立测试集和边界条件，但还可以补充故障处理证据。",
                "evidence_quote": "独立测试集",
                "confidence": "medium",
                "fatal_issues": [],
                "follow_up": "",
            }
            yield ChatEvent("delta", text=json.dumps(result, ensure_ascii=False))

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.create_chat_provider",
        lambda *args, **kwargs: Provider(),
    )
    old_id = _prepare_provider_pending(controller)
    old_profile = controller.profileId
    old_interview["question"] = next(
        q
        for q in controller.service.interview_session(
            controller.profileId, old_id
        )["questions"]
        if q["question_id"] == "q-001"
    )
    _wait_until(stream_started.is_set)

    try:
        if destination == "interview":
            preview = controller.previewInterviewSettings("post_training_engineer", "hard", "", False)
            controller.startConfiguredInterview("post_training_engineer", "hard", "selected", "", False,
                                                preview["context_sha256"])
            assert controller.interview["interview_id"] != old_id
        else:
            assert controller.createLearningProfile("另一份合成档案", "post_training_engineer")
            assert controller.profileId != old_profile
        new_identity = (controller.profileId, controller.interview.get("interview_id"))
        release.set()
        _wait_until(lambda: not controller._provider_interview_tasks and not controller._workers)
        old_session = controller.service.interview_session(old_profile, old_id)
        assert not old_session["assessments"]
        assert new_identity == (controller.profileId, controller.interview.get("interview_id"))
        assert not controller.interviewGrading.get("active") and not controller.busy
    finally:
        release.set()


def test_codex_grading_is_nonblocking_and_can_stop_then_continue(controller):
    """Codex grading leaves busy false and resumes only after explicit continue."""

    starts = []
    interrupts = []
    turn_number = 0

    async def start_thread(**kwargs):
        return {"thread": {"id": "grading-thread"}}

    async def start_turn(*args, **kwargs):
        nonlocal turn_number
        turn_number += 1
        turn_id = f"grading-turn-{turn_number}"
        starts.append(turn_id)
        return {"turn": {"id": turn_id}}

    async def interrupt(thread_id, turn_id):
        interrupts.append((thread_id, turn_id))
        return {}

    controller._codex_backend = SimpleNamespace(
        start_thread=start_thread,
        start_turn=start_turn,
        interrupt=interrupt,
    )
    controller._codex_thread_id = None
    controller._codex_thread_mode = "interviewer"
    controller._codex_pump_started = True
    controller._ensure_codex_loop()

    interview_id = controller.interview["interview_id"]
    profile_id = controller.profileId
    controller.service.answer_interview(
        profile_id, interview_id, "q-001", "合成 Codex 评分答案引用独立测试集。"
    )
    configure_interview_grading(
        controller.repo_root,
        profile_id,
        interview_id,
        connection_id="codex",
        include_materials=False,
    )
    controller.service.finish_interview(
        profile_id, interview_id, summary="合成 Codex 评分测试", confirm_incomplete=True
    )
    controller._load_interview(interview_id)
    key, scope = controller._interview_conversation_consent("codex", False)
    controller._settings.setValue(key, scope)
    controller._start_pending_grading()
    assert not starts and not controller.busy
    controller._handle_codex_connect_ready({"backend": controller._codex_backend,
                                            "thread_id": "connected", "mode": "interviewer"})

    _wait_until(lambda: starts == ["grading-turn-1"])
    assert controller.busy is False
    assert controller.interviewGrading["active"] is True
    assert controller.interview.get("ai_assessment_state") != "streaming"

    assert controller.stopInterviewGrading()
    _wait_until(lambda: bool(interrupts))
    controller._handle_codex_event(
        CodexEvent(
            "turn/completed",
            {"turnId": "grading-turn-1", "status": "cancelled"},
        )
    )
    assert controller.busy is False
    assert controller.interviewGrading["paused"] is True

    assert controller.continueInterviewGrading()
    _wait_until(lambda: starts == ["grading-turn-1", "grading-turn-2"])
    assert controller.busy is False
