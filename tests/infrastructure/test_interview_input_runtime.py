"""Exercise real Qt input/IME behavior and persisted dynamic interview turns."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QInputMethodEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.ai.codex_backend import CodexEvent

REPO = Path(__file__).resolve().parents[2]
QML = REPO / "src/llm_interview_lab/desktop/qml/Main.qml"


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QApplication(["interview-input-tests"])
    if os.name == "nt":
        app.setFont(QFont("Microsoft YaHei UI", 10))
    return app


@pytest.fixture(scope="module")
def public_repo(tmp_path_factory):
    root = tmp_path_factory.mktemp("interview-input-public")
    for name in ("pyproject.toml", ".gitignore"):
        shutil.copy2(REPO / name, root / name)
    for name in ("curriculum", "workspace/schema", "workspace/templates"):
        shutil.copytree(REPO / name, root / name)
    (root / "workspace/profiles").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture
def controller(qapp, public_repo, tmp_path, monkeypatch):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    profile = "input-" + uuid4().hex[:10]
    controller = AppController(public_repo, profile_id=profile, log_root=tmp_path / "logs")
    assert controller.completeOnboarding(profile, "post_training_engineer", "intern", "codex", "{}")
    preview = controller.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
    controller.startDynamicPersonalizedInterview(
        "post_training_engineer", "intern", "hard", "codex", "", False, preview["context_sha256"]
    )
    assert controller.interview["question"]["question_id"] == "q-001"
    yield controller
    controller.shutdown()
    QCoreApplication.processEvents()


@pytest.fixture
def scene(controller):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), "Production Main.qml failed to load"
    window = engine.rootObjects()[0]
    assert isinstance(window, QQuickWindow)
    window.show()
    QTest.qWait(80)
    yield window, controller
    window.close()
    engine.deleteLater()
    QCoreApplication.sendPostedEvents()
    QCoreApplication.processEvents()


def _items(item):
    for child in item.childItems():
        yield child
        yield from _items(child)


def _find(window, name):
    item = next((item for item in _items(window.contentItem()) if item.objectName() == name), None)
    assert item is not None, name
    return item


def _click(window, item):
    point = item.mapToScene(QPointF(item.width() / 2, min(20, item.height() / 2)))
    QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(round(point.x()), round(point.y())))
    QCoreApplication.processEvents()


def _visible_hints(editor):
    return [
        item for item in _items(editor)
        if "Placeholder" in item.metaObject().className()
        and item.property("visible") and item.property("opacity") > 0
        and item.property("text") and item.property("color").alpha() > 0
    ]


def _capture(window, name):
    directory = os.environ.get("LLM_LAB_UI_EVIDENCE_DIR")
    if directory:
        QTest.qWait(150)  # Let the production hover/theme transition settle.
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        assert window.grabWindow().save(str(destination / f"{name}.png"))


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_long_toast_grows_without_clipping(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.toast.emit("当前模型要求更新版本的 Codex，连接成功不代表模型可用。请到设置中选择新版 Codex，或换用当前 Codex 支持的模型，再重新连接。回答已保留。")
    QTest.qWait(200)
    popup = window.findChild(QObject, "globalToast")
    content = popup.property("contentItem")
    assert popup.property("visible")
    assert content.property("contentHeight") <= content.height() + 1
    assert popup.property("height") >= content.property("implicitHeight") + 28
    _capture(window, f"long-error-{size[0]}")


def test_onboarding_does_not_preview_a_nonexistent_practice_task(qapp, public_repo, tmp_path, monkeypatch):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "fresh-settings"))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    profile = "fresh-" + uuid4().hex[:10]
    controller = AppController(public_repo, profile_id=profile)
    messages = []
    controller.toast.connect(messages.append)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML)))
    window = engine.rootObjects()[0]
    try:
        window.show()
        QTest.qWait(80)
        assert controller.completeOnboarding(profile, "post_training_engineer", "intern", "disabled", "{}")
        QTest.qWait(80)
        assert controller.currentTask.get("problem_id")
        assert not messages, messages
        controller.navigate("coach")
        QTest.qWait(80)
        coach = window.findChild(QObject, "coachPage")
        assert coach.property("preview")["parts"], "An opened task still has a usable Coach preview"
    finally:
        controller.shutdown()
        window.close()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents()


@pytest.mark.parametrize("action", ["stop", "timeout"])
def test_codex_request_can_stop_without_losing_the_locked_answer(scene, action):
    window, controller = scene
    controller.lockInterviewAnswer("合成回答：我先划分训练集与验证集，再检查相互之间的数据泄漏。")
    interview_id = controller.interview["interview_id"]
    saved_answer = controller.interview["answer_text"]

    class Transport:
        closed = False
        interrupts = []

        async def start_turn(self, *args, **kwargs):
            return {"turn": {"id": "turn-stop-test"}}

        async def interrupt(self, thread_id, turn_id):
            self.interrupts.append((thread_id, turn_id))
            controller._codexEventReceived.emit(CodexEvent("turn/completed", {
                "turnId": turn_id, "turn": {"id": turn_id, "status": "interrupted"},
            }))
            return {}

        async def close(self):
            self.closed = True

    backend = Transport()
    controller._codex_backend = backend
    controller._codex_thread_id = "thread-stop-test"
    controller._codex_thread_mode = "interviewer"
    controller._ensure_codex_loop()
    controller.aiStateChanged.emit()
    assert controller.sendCodexInterviewAnswer(saved_answer, False)
    for _ in range(50):
        QTest.qWait(20)
        if controller._codex_interview_turn_id == "turn-stop-test":
            break
    operation = controller._codex_interview_operation_id
    if action == "stop":
        _click(window, _find(window, "stopCodexInterviewRequest"))
    else:
        controller._expire_codex_interview_turn("old-operation")
        assert controller.busy and controller._codex_backend is backend
        controller._expire_codex_interview_turn(operation)
    for _ in range(50):
        QTest.qWait(20)
        if not controller.busy and (backend.interrupts if action == "stop" else backend.closed):
            break
    assert not controller.busy
    assert controller.interview["question"]["question_id"] == "q-001"
    assert controller.service.interview_answer_text(controller.profileId, interview_id, "q-001") == saved_answer
    assert not controller.service.interview_session(controller.profileId, interview_id)["assessments"]
    assert "回答已保留" in controller.interview["ai_error"]
    assert _find(window, "globalAiStatus").property("text") == ("AI 已停止" if action == "stop" else "AI 请求失败")
    if action == "stop":
        assert backend.interrupts == [("thread-stop-test", "turn-stop-test")]
    else:
        assert backend.closed and controller._codex_backend is None


def test_answer_hint_hides_on_focus_ime_and_committed_text(scene):
    window, controller = scene
    controller.setTheme("dark")
    answer = _find(window, "interviewAnswerEditor")
    assert _visible_hints(answer), "An empty, unfocused input should offer a hint"
    _click(window, answer)
    _capture(window, "answer-focused-before-input")
    assert not _visible_hints(answer), "Focusing an input must hide its hint before IME starts"
    event = QInputMethodEvent("hong", [])
    QCoreApplication.sendEvent(answer, event)
    assert answer.property("preeditText") == "hong"
    assert not _visible_hints(answer)
    committed = QInputMethodEvent()
    committed.setCommitString("这是一份合成测试回答。")
    QCoreApplication.sendEvent(answer, committed)
    QCoreApplication.processEvents()
    assert answer.property("text") == "这是一份合成测试回答。"
    assert not _visible_hints(answer)
    assert answer.property("topInset") == 0
    _capture(window, "answer-typed-dark")
    answer.setProperty("text", "")
    answer.setProperty("focus", False)
    QCoreApplication.processEvents()
    assert _visible_hints(answer), "Clearing and leaving the input restores the hint"


def test_question_switch_clears_drafts_without_touching_saved_answer(scene):
    window, controller = scene
    answer = _find(window, "interviewAnswerEditor")
    evidence = _find(window, "interviewEvidenceEditor")
    followup = _find(window, "interviewFollowupEditor")
    draft = "Synthetic answer: held-out evaluation and a rollback threshold."
    answer.setProperty("text", draft)
    evidence.setProperty("text", "Old local evidence draft")
    followup.setProperty("text", "Old local follow-up draft")
    controller.navigate("home")
    controller.navigate("interview")
    QCoreApplication.processEvents()
    assert answer.property("text") == draft
    controller.lockInterviewAnswer(draft)
    interview_id = controller.interview["interview_id"]
    controller.service.score_interview(
        controller.profileId, interview_id, "q-001",
        {key: 3 for key in controller.interview["question"]["rubric"]["dimensions"]},
        evidence="The answer names held-out evaluation and a rollback threshold.",
        source="ai", confidence="medium",
    )
    current = controller.service.interview_session(controller.profileId, interview_id)
    controller.service.append_dynamic_interview_question(
        controller.profileId, interview_id,
        question={"kind": current["questions"][0]["kind"], "title": "合成追问", "prompt": "怎样验证这次改动的实际效果？"},
        context_sha256=current["plan_context_sha256"],
    )
    controller._load_interview(interview_id)
    QTest.qWait(30)
    assert answer.property("text") == ""
    assert evidence.property("text") == ""
    assert followup.property("text") == ""
    session = controller.service.interview_session(controller.profileId, interview_id)
    assert "q-001" in session["answers"] and "q-001" in session["assessments"]
    assert controller.service.interview_answer_text(controller.profileId, interview_id, "q-001") == draft


def test_ui_lock_preview_codex_response_enters_next_question(scene):
    window, controller = scene
    errors = []
    controller.toast.connect(errors.append)

    class FakeCodex:
        calls = []

        async def start_turn(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return {"turn": {"id": "turn-input-test"}}

    backend = FakeCodex()
    controller._codex_backend = backend
    controller._codex_thread_id = "thread-input-test"
    controller._codex_thread_mode = "interviewer"
    controller._ai_status = "Codex 已连接"
    controller._ensure_codex_loop()
    controller.aiStateChanged.emit()
    controller.setTheme("dark")
    answer = _find(window, "interviewAnswerEditor")
    draft = "合成回答：我先测量失败率，再在独立验证集上核对改动效果。"
    answer.setProperty("text", draft)
    _click(window, _find(window, "lockInterviewAnswer"))
    dialog = window.findChild(QObject, "lockInterviewAnswerDialog")
    assert dialog.property("opened") or dialog.property("visible")
    QMetaObject.invokeMethod(dialog, "accept")
    for _ in range(30):
        QTest.qWait(20)
        if not dialog.property("visible"):
            break
    assert not dialog.property("visible"), "Wait for the modal lock confirmation to close"
    assert controller.interview["answer_locked"]
    assert not _find(window, "recordSelfAssessment").isVisible()
    continuation = _find(window, "continueCodexInterview")
    assert continuation.isVisible() and continuation.isEnabled()
    clicks = []
    continuation.clicked.connect(lambda: clicks.append("clicked"))
    _capture(window, "dynamic-answer-locked-dark")
    _click(window, continuation)
    QTest.qWait(80)
    _capture(window, "dynamic-answer-context-dark")
    preview = window.findChild(QObject, "interviewAnswerContextDialog")
    assert clicks == ["clicked"]
    assert preview.property("visible"), errors
    assert not backend.calls, "Preview alone must not send the answer"
    _click(window, _find(window, "confirmInterviewAnswerContext"))
    for _ in range(30):
        QTest.qWait(20)
        if controller._codex_interview_turn_id == "turn-input-test":
            break
    assert len(backend.calls) == 1
    assert draft in backend.calls[0][0][1]
    result = {
        "scores": {key: 3 for key in controller.interview["question"]["rubric"]["dimensions"]},
        "evidence": "候选人说明了先测量失败率，并使用独立验证集核对改动效果。",
        "confidence": "medium", "fatal_issues": [],
        "follow_up": "你怎样选择验证集，并排除训练数据泄漏？",
    }
    for method, extra in (
        ("turn/started", {}),
        ("item/agentMessage/delta", {"delta": json.dumps(result)}),
        ("turn/completed", {"status": "completed"}),
    ):
        controller._handle_codex_event(CodexEvent(method, {"turnId": "turn-input-test", **extra}))
        QCoreApplication.processEvents()
    QTest.qWait(80)
    assert controller.interview["question"]["question_id"] == "q-002"
    assert controller.interview["question"]["prompt"] == result["follow_up"]
    assert answer.property("text") == ""
    assert controller.busy is False
    _capture(window, "dynamic-second-question-dark")


@pytest.mark.parametrize("mode", ["codex", "provider"])
def test_dynamic_followups_advance_once_without_duplicate_scoring(controller, monkeypatch, mode):
    errors = []
    controller.toast.connect(errors.append)
    interview_id = controller.interview["interview_id"]
    for index in (1, 2):
        question_id = f"q-{index:03d}"
        controller.lockInterviewAnswer("I measured the failure rate and tested a held-out baseline.")
        result = {
            "scores": {name: 3 for name in controller.interview["question"]["rubric"]["dimensions"]},
            "evidence": "The answer describes measuring failure rates and testing a held-out baseline.",
            "confidence": "medium", "fatal_issues": [],
            "follow_up": f"第 {index + 1} 问：你怎样验证这次改动的效果？",
        }
        if mode == "codex":
            operation = f"test-followup-{index}"
            identity = (controller.profileId, interview_id, question_id, operation, "codex")
            controller._codex_interview_identity = identity
            controller._codex_interview_operation_id = operation
            controller._codex_interview_buffer = json.dumps(result)
            controller._finish_codex_interview_assessment(identity)
        else:
            monkeypatch.setattr(controller, "_background", lambda operation, complete, failed=None: complete(result))
            controller.assessInterviewWithProvider("", "fake-connection", False)
        assert not errors, errors
        assert controller.interview["question"]["question_id"] == f"q-{index + 1:03d}"
        session = controller.service.interview_session(controller.profileId, interview_id)
        assert len(session["questions"]) == index + 1
        assert len(session["assessments"]) == index


@pytest.mark.parametrize("size", [(900, 620), (1080, 680), (1280, 800), (1440, 900)])
def test_answer_geometry_at_supported_sizes(scene, size):
    window, controller = scene
    window.resize(*size)
    for theme, scale in (("light", 1.0), ("dark", 1.25)):
        controller.setTheme(theme)
        window.setProperty("displayFontScaleOverride", scale)
        QTest.qWait(50)
        answer = _find(window, "interviewAnswerEditor")
        _click(window, answer)
        answer.setProperty("text", "合成测试回答：说明本人完成的工作、实验依据与结果。")
        QCoreApplication.processEvents()
        rectangle = answer.property("cursorRectangle")
        assert answer.property("topInset") == 0
        assert rectangle.y() >= answer.property("topPadding") - 1
        assert rectangle.bottom() < answer.height()
        assert answer.width() >= 260
        assert not _visible_hints(answer)
        button = _find(window, "lockInterviewAnswer")
        hint = _find(window, "interviewAnswerActionHint")
        button_start = button.mapToScene(QPointF(0, 0))
        hint_start = hint.mapToScene(QPointF(0, 0))
        assert (
            hint_start.y() + hint.height() <= button_start.y()
            or hint_start.x() + hint.width() <= button_start.x()
        ), "Submit button must not overlap its explanation"
        assert button.isEnabled()
        assert button.property("resolvedBackground") != button.property("resolvedForeground")
        _capture(window, f"interview-{size[0]}x{size[1]}-{theme}")
        viewport = _find(window, "interviewQuestionScroll")
        flickable = viewport.property("contentItem")
        # Small windows must allow scrolling the complete submit action into view.
        flickable.setProperty("contentY", max(0, flickable.property("contentHeight") - flickable.height()))
        QTest.qWait(30)
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        local = viewport.mapFromScene(point)
        assert 0 <= local.x() <= viewport.width()
        assert 0 <= local.y() - button.height() / 2
        assert local.y() + button.height() / 2 <= viewport.height()
        if size == (900, 620):
            _capture(window, f"interview-900x620-{theme}-submit")
        flickable.setProperty("contentY", 0)
