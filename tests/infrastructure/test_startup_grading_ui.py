"""Restart real saved interviews and operate Home while end grading is pending.

Only the network is synthetic; QML, Profile restoration, answers and grading
records use the production path. No real Profile, key or material is read.
"""

import asyncio
import json
import threading
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from llm_interview_lab.ai.base import ChatEvent, ConnectionResult
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.role_interviews import configure_interview_grading
from tests.infrastructure.test_interview_input_runtime import (
    QML, qapp, public_repo, controller, _find, _items, _click,
    _capture, _within_window, _wait_for_asr,
)
from tests.infrastructure.test_question_first_desktop import provider_scene


@pytest.fixture
def restored_scoring_home(controller, tmp_path, monkeypatch):
    iid = provider_scene(controller)
    service, profile = controller.service, controller.profileId
    service.answer_interview(profile, iid, "q-001", "我使用独立评测集验证合成实验。")
    configure_interview_grading(controller.repo_root, profile, iid,
                               connection_id="selected", include_materials=False)
    service.finish_interview(profile, iid, summary="合成重启验收", confirm_incomplete=True)
    question = service.interview_session(profile, iid)["questions"][0]
    controller.shutdown()
    state = SimpleNamespace(requests=0, probes=0, fail_next=False,
                            release=threading.Event(), cancelled=0)

    class Provider:
        async def test_connection(self):
            state.probes += 1
            return ConnectionResult(True, "合成连接成功")

        async def stream_chat(self, *args, **kwargs):
            state.requests += 1
            try:
                while not state.release.is_set():
                    await asyncio.sleep(.02)
            except asyncio.CancelledError:
                state.cancelled += 1
                raise
            if state.fail_next:
                state.fail_next = False
                raise RuntimeError("合成网络超时；可重试本题评分。")
            reply = {
                "scores": {dimension: 3 for dimension in question["rubric"]["dimensions"]},
                "evidence": "回答明确提及独立评测集，但尚缺具体划分和防止数据泄漏的实现证据。",
                "evidence_quote": "独立评测集", "confidence": "medium",
                "fatal_issues": [], "follow_up": "",
            }
            yield ChatEvent("delta", text=json.dumps(reply, ensure_ascii=False))

    monkeypatch.setattr("llm_interview_lab.desktop.controller.create_chat_provider",
                        lambda *args, **kwargs: Provider())
    restored = AppController(controller.repo_root, log_root=tmp_path / "restart-logs")
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(value.toString() for value in values))
    engine.rootContext().setContextProperty("backend", restored)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.show()
    try:
        assert _wait_for_asr(lambda: state.requests == 1 and state.probes == 1)
        assert restored.profileId == profile and restored.currentPage == "home"
        yield SimpleNamespace(window=window, controller=restored, transport=state,
                              service=service, profile=profile, iid=iid)
        assert not warnings, "\n".join(warnings)
    finally:
        state.release.set()
        window.close()
        restored.shutdown()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents()
        QCoreApplication.processEvents()


def _assert_home_unblocked(window, controller):
    primary = _find(window, "homePrimaryAction")
    assert not controller.busy
    assert controller.interview.get("ai_assessment_state") != "streaming"
    assert primary.property("enabled") and not primary.property("busy")
    spinners = [item for item in _items(window.contentItem())
                if "LabBusyIndicator" in item.metaObject().className()
                and item.property("visible") and item.property("running")]
    assert not spinners, "Background grading must not show anonymous foreground spinners"


@pytest.mark.parametrize("width,height,theme,scale", [
    (900, 620, "dark", 1.25), (1280, 800, "light", 1.0),
])
def test_restart_grading_stop_continue_and_home_layout(restored_scoring_home, width, height, theme, scale):
    case = restored_scoring_home
    window, restored, transport = case.window, case.controller, case.transport
    window.resize(width, height)
    restored.setTheme(theme)
    window.setProperty("displayFontScaleOverride", scale)
    QTest.qWait(80)
    _assert_home_unblocked(window, restored)
    status = _find(window, "homeGradingMessage")
    stop = _find(window, "homeStopGrading")
    assert status.property("visible") and "评分" in status.property("text")
    assert _within_window(window, status) and _within_window(window, stop)
    assert _within_window(window, _find(window, "homePrimaryAction"))
    _capture(window, f"startup-grading-home-{theme}-{width}")

    _click(window, stop)
    assert _wait_for_asr(lambda: transport.cancelled == 1)
    QTest.qWait(100)
    assert transport.requests == 1, "Stopping must not immediately restart the next grading task"
    assert not case.service.interview_session(case.profile, case.iid)["assessments"]
    _assert_home_unblocked(window, restored)
    resume = _find(window, "homeContinueGrading")
    assert resume.property("visible") and resume.property("enabled")
    _click(window, resume)
    assert _wait_for_asr(lambda: transport.requests == 2)
    transport.release.set()
    assert _wait_for_asr(lambda: "q-001" in case.service.interview_session(case.profile, case.iid)["assessments"])
    _assert_home_unblocked(window, restored)
    restored.retryInterviewGrading()
    QTest.qWait(80)
    assert transport.requests == 2, "Successful scores must not be requested again"


def test_startup_grading_failure_can_retry_without_locking_home(restored_scoring_home):
    case = restored_scoring_home
    case.transport.fail_next = True
    case.transport.release.set()
    assert _wait_for_asr(lambda: case.service.interview_session(case.profile, case.iid)
                        ["grading"]["questions"]["q-001"]["status"] == "failed")
    _assert_home_unblocked(case.window, case.controller)
    status = _find(case.window, "homeGradingMessage")
    assert status.property("visible") and "失败" in status.property("text")
    resume = _find(case.window, "homeContinueGrading")
    assert resume.property("visible") and resume.property("enabled")
    _click(case.window, resume)
    assert _wait_for_asr(lambda: "q-001" in case.service.interview_session(case.profile, case.iid)["assessments"])
    assert case.transport.requests == 2
    _assert_home_unblocked(case.window, case.controller)


def test_startup_grading_does_not_block_home_start_action(restored_scoring_home):
    case = restored_scoring_home
    _assert_home_unblocked(case.window, case.controller)
    _click(case.window, _find(case.window, "homePrimaryAction"))
    assert case.controller.currentPage == "interview"
    assert _find(case.window, "startConfiguredInterview").property("visible")
    assert not case.controller.busy


def test_report_navigation_and_refresh_keep_grading_resumable(restored_scoring_home):
    case = restored_scoring_home
    _click(case.window, _find(case.window, "homeViewGrading"))
    assert case.controller.currentPage == "interview"
    assert case.controller.interviewGrading["active"]
    assert case.transport.requests == 1  # Reading this report does not cancel/restart it.
    assert _find(case.window, "stopInterviewGrading").property("visible")
    assert not _find(case.window, "retryInterviewGrading").property("visible")
    case.controller.refresh()
    assert _wait_for_asr(lambda: case.transport.cancelled == 1)
    assert case.controller.interviewGrading["paused"]
    assert not case.controller.interviewGrading["active"]
    assert case.transport.requests == 1
    case.transport.release.set()
    case.controller.retryInterviewGrading()
    assert _wait_for_asr(lambda: "q-001" in case.service.interview_session(case.profile, case.iid)["assessments"])
    assert case.transport.requests == 2
