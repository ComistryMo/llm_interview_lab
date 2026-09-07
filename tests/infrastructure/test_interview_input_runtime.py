"""Exercise real Qt input/IME behavior and persisted dynamic interview turns."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time
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
    # The explicit organization/application constructor uses NativeFormat on
    # Windows even after setDefaultFormat. Redirect that constructor as well.
    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings", lambda *args: QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
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
    qml_errors = []
    engine.warnings.connect(lambda values: qml_errors.extend(value.toString() for value in values))
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), qml_errors
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


def _enter_coding_round(controller):
    """Prepare a real persisted session; replies here are fixture data, not AI evidence."""
    for stage in ("experience", "experience", "theory", "theory", "coding"):
        question = controller.interview["question"]
        controller.lockInterviewAnswer("合成验收回答：我负责偏好数据去重，用独立留出集验证。")
        preview = controller.interviewContextPreview(controller.interview["answer_text"], False)
        assert preview["parts"]
        controller.service.advance_dynamic_interview(
            controller.profileId, controller.interview["interview_id"], question["question_id"],
            {"scores": {name: 3 for name in question["rubric"]["dimensions"]},
             "evidence": "合成验收数据，仅用于界面测试。", "confidence": "medium", "fatal_issues": [],
             "next_stage": stage, "follow_up": "如何验证你提到的数据去重？" if stage != "coding" else "",
             "coding_problem_id": "FND-002" if stage == "coding" else "",
             "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))]
                               if stage != "coding" else []},
            context_sha256=controller._interview_context_confirmation[-1],
        )
        controller._load_interview(controller.interview["interview_id"])
    assert controller.interview["question"]["kind"] == "coding"
    QTest.qWait(100)


def _within_window(window, item):
    start = item.mapToScene(QPointF())
    return (start.x() >= 0 and start.y() >= 0
            and start.x() + item.width() <= window.width() + 1
            and start.y() + item.height() <= window.height() + 1)


@pytest.mark.parametrize("size", [(900, 620), (1080, 680), (1280, 800), (1440, 900)])
def test_coding_actions_stay_visible_while_reading_question(scene, size):
    window, controller = scene
    window.resize(*size)
    _enter_coding_round(controller)
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    for theme, scale in (("dark", 1.25), ("light", 1.0)):
        controller.setTheme(theme)
        window.setProperty("displayFontScaleOverride", scale)
        for show_code in (False, True):
            if show_code:
                _click(window, _find(window, "toggleInterviewCodingPrompt"))
            viewport.setProperty("contentY", 0)
            QTest.qWait(80)
            for name in ("runInterviewGrader", "recordInterviewCodingRound", "toggleInterviewCodingPrompt"):
                assert _within_window(window, _find(window, name)), name
            status = _find(window, "interviewCodingStatus")
            assert status.property("contentHeight") <= status.height() + 1
            assert viewport.height() > 130
            _capture(window, f"coding-{'editor' if show_code else 'question'}-{size[0]}-{theme}")
        _click(window, _find(window, "toggleInterviewCodingPrompt"))


def test_edit_saved_connection_reveals_form(scene):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    assert controller.saveConnection("ux-local", "ollama", "synthetic-model", "本地模型（未测试）",
                                     "http://localhost:11434", "", "low")
    controller.navigate("connections")
    QTest.qWait(150)
    button = _find(window, "editConnection")
    page = button.parentItem()
    while page.property("editingConnectionId") is None:
        page = page.parentItem()
    page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
    QTest.qWait(100)
    _click(window, button)
    QTest.qWait(150)
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    _capture(window, "connection-edit-small")
    assert page.property("editingConnectionId") == "ux-local"
    for name in ("saveAndTestConnection", "connectionModelField"):
        control = _find(window, name)
        top = control.mapToItem(page, QPointF()).y()
        assert 0 <= top and top + control.height() <= page.height()
    assert _find(window, "connectionModelField").hasActiveFocus()
    assert _find(window, "saveAndTestConnection").property("variant") == "primary"


def test_saved_connection_card_fits_large_text_and_never_implies_ready(scene):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    assert controller.saveConnection("ux-local", "ollama", "synthetic-model", "本地模型（尚未测试连接）",
                                     "http://localhost:11434", "", "low")
    controller.navigate("connections")
    QTest.qWait(150)
    card = _find(window, "savedConnectionCard")
    page = card.parentItem()
    while page.property("editingConnectionId") is None:
        page = page.parentItem()
    page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
    window.findChild(QObject, "globalToast").setProperty("visible", False)
    QTest.qWait(80)
    pill = _find(window, "savedConnectionStatus")
    assert controller.connections[0]["ready"] is False
    assert pill.property("tone") == page.property("theme").property("muted")
    for item in _items(card):
        if item.isVisible() and (item.property("text") or item.objectName() == "editConnection"):
            assert item.mapToItem(card, QPointF(0, item.height())).y() <= card.height() + 1
    _capture(window, "connection-saved-small")


@pytest.mark.parametrize("entry", ["button", "shortcut"])
def test_interview_coding_runs_visible_revision_and_shows_failure(scene, entry):
    window, controller = scene
    window.resize(1080, 680)
    _enter_coding_round(controller)
    # Practice output must never appear as the current interview's evidence.
    controller._test_output = "unrelated Practice PASS"
    controller.stateChanged.emit()
    assert "unrelated" not in _find(window, "interviewCodingOutput").property("text")
    _click(window, _find(window, "toggleInterviewCodingPrompt"))
    editor = _find(window, "interviewCodingEditor")
    editor.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
    edit = QInputMethodEvent()
    edit.setCommitString("\n# UAT latest editor revision\n")
    QCoreApplication.sendEvent(editor, edit)
    latest = editor.property("text")
    assert "UAT latest editor revision" in latest
    digest = hashlib.sha256(latest.encode()).hexdigest()
    if entry == "shortcut":
        QTest.keyClick(window, Qt.Key_R, Qt.ControlModifier)
    else:
        _click(window, _find(window, "runInterviewGrader"))
    deadline = time.monotonic() + 30
    while controller.busy and time.monotonic() < deadline:
        QTest.qWait(50)
        time.sleep(0.01)
    assert not controller.busy
    assert controller.interview["coding_tested_revision"] == digest
    assert controller.interview["coding_test_status"] == "failed"  # Intentionally incomplete starter, real Grader.
    status = _find(window, "interviewCodingStatus")
    assert "测试未通过" in status.property("text") and digest[:7] in status.property("text")
    assert status.property("tone") == "danger"
    assert "FAILED" in _find(window, "interviewCodingOutput").property("text")
    assert _find(window, "recordInterviewCodingRound").isEnabled()
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    viewport.setProperty("contentY", max(0, viewport.property("contentHeight") - viewport.height()))
    QTest.qWait(100)
    _capture(window, f"coding-failed-{entry}")
    if entry == "button":
        _click(window, _find(window, "recordInterviewCodingRound"))
        QTest.qWait(100)
        assert not controller.interview.get("question")
        assert controller.interview["status"] == "active"
        assert _find(window, "interviewQuestionTitle").property("text") == "本场作答已完成"
        assert _find(window, "finishInterviewButton").property("text") == "结束并查看复盘"
        _capture(window, "interview-ready-to-finish")
        _click(window, _find(window, "finishInterviewButton"))
        dialog = window.findChild(QObject, "interviewFinishDialog")
        assert dialog is not None and dialog.property("visible")
        QMetaObject.invokeMethod(dialog, "accept")
        QTest.qWait(100)
        assert controller.interview["status"] == "completed"
        assert not _find(window, "finishInterviewButton").isVisible()
        _capture(window, "interview-completed-report")
        return
    editor.forceActiveFocus()
    edit.setCommitString("# modified after test\n")
    QCoreApplication.sendEvent(editor, edit)
    assert not _find(window, "recordInterviewCodingRound").isEnabled()
    assert "代码已修改" in status.property("text")
    # Reload reads only this question's persisted result, not the global output.
    controller._test_output = "unrelated Practice PASS"
    controller._load_interview(controller.interview["interview_id"])
    assert controller.interview["coding_test_status"] == "failed"
    assert "unrelated" not in controller.interview["coding_test_output"]


def test_interview_completion_copy_matches_session_state(scene):
    window, controller = scene
    controller.finishInterview()
    QTest.qWait(100)
    assert not _find(window, "finishInterviewButton").isVisible()
    assert _find(window, "configureAnotherInterview").isVisible()
    assert "选择岗位" not in _find(window, "interviewQuestionPrompt").property("text")
    assert _find(window, "interviewQuestionTitle").property("text") == "本场复盘"
    _capture(window, "interview-finished")


def test_profile_switch_preserves_unsent_interview_answer(scene, tmp_path):
    window, controller = scene
    original_profile = controller.profileId
    other_id = "other-" + uuid4().hex[:10]
    other = AppController(controller.repo_root, profile_id=other_id, log_root=tmp_path / "other-logs")
    try:
        assert other.completeOnboarding(other_id, "post_training_engineer", "intern", "codex", "{}")
        preview = other.dynamicInterviewContextPreview("post_training_engineer", "intern", "hard", "", False)
        other.startDynamicPersonalizedInterview("post_training_engineer", "intern", "hard", "codex", "", False,
                                               preview["context_sha256"])
        assert other.interview["interview_id"] == controller.interview["interview_id"]
    finally:
        other.shutdown()
    editor = _find(window, "interviewAnswerEditor")
    _click(window, editor)
    edit = QInputMethodEvent()
    edit.setCommitString("尚未提交的合成回答，不应带入其他学习档案。")
    QCoreApplication.sendEvent(editor, edit)
    controller.navigate("settings")
    assert not controller.switchProfile(other_id), "Switch must not silently discard or carry over an unsent answer"
    assert controller.profileId == original_profile
    controller.navigate("interview")
    assert "尚未提交" in editor.property("text")
    controller.lockInterviewAnswer(editor.property("text"))
    QTest.qWait(50)
    assert controller.switchProfile(other_id)
    controller.navigate("interview")
    QTest.qWait(50)
    assert editor.property("text") == ""
    assert controller.switchProfile(original_profile)
    controller.navigate("interview")
    QTest.qWait(50)
    assert "尚未提交" in editor.property("text")


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


def test_settings_saves_model_and_reasoning_from_the_same_edit(scene):
    window, controller = scene
    controller.setCodexModel("")
    controller.setCodexReasoningEffort("")
    controller.navigate("settings")
    QTest.qWait(100)
    _find(window, "codexModelField").setProperty("text", "selected-model")
    _find(window, "codexReasoningEffort").setProperty("currentIndex", 1)
    button = _find(window, "saveCodexModelPreferences")
    ancestor = button.parentItem()
    while ancestor:
        if ancestor.property("contentY") is not None:
            ancestor.setProperty("contentY", button.mapToItem(ancestor, QPointF()).y() - 50)
        ancestor = ancestor.parentItem()
    QTest.qWait(50)
    _click(window, button)
    assert controller.codexModel == "selected-model"
    assert controller.codexReasoningEffort == "low"
    controller.navigate("home")
    controller.navigate("settings")
    QTest.qWait(50)
    assert _find(window, "codexReasoningEffort").property("currentValue") == "low"


def test_setup_requires_consent_for_resume_and_jd(scene, tmp_path):
    window, controller = scene
    for name, kind in (("resume", "resume"), ("jd", "job_description")):
        source = tmp_path / (name + ".txt")
        source.write_text("合成材料：后训练实习岗位，偏好数据与实验评估。", encoding="utf-8")
        assert controller.addMaterial(str(source), kind, name, True)
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 2)
    _find(window, "interviewUseMaterials").setProperty("checked", True)
    _find(window, "interviewPrimaryMaterial").setProperty("currentIndex", 0)
    _find(window, "interviewUseAdditionalMaterial").setProperty("checked", True)
    _find(window, "interviewAdditionalMaterial").setProperty("currentIndex", 1)
    QTest.qWait(80)
    button = _find(window, "startConfiguredInterview")
    assert not button.isEnabled()
    _find(window, "interviewMaterialConsent").setProperty("checked", True)
    assert button.isEnabled()
    _click(window, button)
    QTest.qWait(100)
    _click(window, _find(window, "confirmInterviewSetupContext"))
    QTest.qWait(100)
    session = controller.service.interview_session(controller.profileId, controller.interview["interview_id"])
    assert session["status"] == "active" and len(session["questions"]) == 1
    assert {ref["kind"] for ref in session["material_refs"]} == {"resume", "job_description"}


def test_report_recognizes_qvariant_evidence_as_scored(scene):
    window, controller = scene
    controller.lockInterviewAnswer("合成回答：明确说明了独立留出评估与数据去重过程。")
    question = controller.interview["question"]
    controller.service.score_interview(
        controller.profileId, controller.interview["interview_id"], question["question_id"],
        {name: 3 for name in question["rubric"]["dimensions"]},
        evidence="回答描述了独立留出评估和数据去重过程，缺少具体量化结果。", source="ai", confidence="medium",
    )
    controller.finishInterview()
    QTest.qWait(80)
    summary = _find(window, "interviewResultSummary").property("text")
    assert "部分证据分数" in summary and "尚未评分" not in summary
    assert format(controller.interview["result"]["overall_score"], "g") in summary


def test_onboarding_does_not_preview_a_nonexistent_practice_task(qapp, public_repo, tmp_path, monkeypatch):
    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings", lambda *args: QSettings(str(tmp_path / "fresh-settings.ini"), QSettings.IniFormat))
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

        async def start_thread(self, **kwargs):
            return {"thread": {"id": "thread-stop-test"}}

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
    controller.interviewContextPreview(saved_answer, False)
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


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_ui_lock_preview_codex_response_enters_next_question(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    errors = []
    controller.toast.connect(errors.append)

    class FakeCodex:
        calls = []

        async def start_thread(self, **kwargs):
            return {"thread": {"id": "thread-input-fresh"}}

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
    pos = continuation.mapToScene(QPointF())
    assert 0 <= pos.y() and pos.y() + continuation.height() <= window.height()
    viewport = _find(window, "interviewQuestionScroll")
    assert pos.y() >= viewport.mapToScene(QPointF(0, viewport.height())).y()
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
        "next_stage": "experience", "coding_problem_id": "",
        "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
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
        controller.interviewContextPreview(controller.interview["answer_text"], False)
        result = {
            "scores": {name: 3 for name in controller.interview["question"]["rubric"]["dimensions"]},
            "evidence": "The answer describes measuring failure rates and testing a held-out baseline.",
            "confidence": "medium", "fatal_issues": [],
            "follow_up": f"第 {index + 1} 问：你怎样验证这次改动的效果？",
            "next_stage": "experience", "coding_problem_id": "",
            "next_skill_ids": [next(iter(controller.service.roles.roles["post_training_engineer"].skill_weights))],
        }
        if mode == "codex":
            operation = f"test-followup-{index}"
            identity = (controller.profileId, interview_id, question_id, operation, "codex")
            controller._codex_interview_identity = identity
            controller._codex_interview_operation_id = operation
            controller._codex_interview_buffer = json.dumps(result)
            controller._codex_interview_include_materials = False
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
    for theme, scale in (("light", 1.0), ("dark", 1.0), ("light", 1.25), ("dark", 1.25)):
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
        title = _find(window, "interviewQuestionTitle")
        prompt = _find(window, "interviewQuestionPrompt")
        assert title.property("contentHeight") <= title.height() + 1
        assert prompt.property("contentHeight") <= prompt.height() + 1
        assert title.mapToScene(QPointF(0, title.height())).y() <= prompt.mapToScene(QPointF()).y()
        assert prompt.mapToScene(QPointF(0, prompt.height())).y() <= answer.mapToScene(QPointF()).y()
        _capture(window, f"interview-{size[0]}x{size[1]}-{theme}-{scale}")
        viewport = _find(window, "interviewQuestionScroll")
        flickable = viewport.property("contentItem")
        # The primary action stays below the question viewport, even when a
        # long question or enlarged text requires scrolling the reading area.
        assert button_start.y() >= viewport.mapToScene(QPointF(0, viewport.height())).y()
        flickable.setProperty("contentY", max(0, flickable.property("contentHeight") - flickable.height()))
        QTest.qWait(30)
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        assert 0 <= point.x() - button.width() / 2
        assert point.x() + button.width() / 2 <= window.width()
        assert 0 <= point.y() - button.height() / 2
        assert point.y() + button.height() / 2 <= window.height()
        if size == (900, 620):
            _capture(window, f"interview-900x620-{theme}-{scale}-submit")
        flickable.setProperty("contentY", 0)


@pytest.mark.parametrize("size", [(900, 620), (1280, 800)])
def test_context_dialog_long_labels_scale_without_overlap(scene, size):
    window, controller = scene
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme("dark")
    controller.lockInterviewAnswer("合成回答：在独立验证集上评估，不能使用训练数据证明效果。")
    page = _find(window, "interviewAnswerEditor")
    while page.property("aiPreview") is None:
        page = page.parentItem()
    parts = [
        {"id": "policy", "selected": True},
        {"id": "candidate_answer", "selected": True},
        {"id": "material:synthetic", "label": "授权材料：合成测试材料 · 后训练实习项目与评测记录（多行长标题用于排版验证，不含真实材料）" * 2,
         "selected": True, "sensitive": True, "sha256": "a" * 64},
    ]
    for property_name, dialog_name, list_name in (
        ("aiPreview", "interviewAnswerContextDialog", "interviewAnswerContextList"),
        ("planContext", "personalizedInterviewContextDialog", "interviewSetupContextList"),
    ):
        page.setProperty(property_name, {"parts": parts, "estimated_tokens": 1500})
        dialog = window.findChild(QObject, dialog_name)
        QMetaObject.invokeMethod(dialog, "open")
        QTest.qWait(180)
        listing = _find(window, list_name)
        rows = sorted((item for item in _items(listing) if item.objectName() == "contextPreviewRow"), key=lambda item: item.y())
        assert len(rows) == 3
        for row in rows:
            labels = [item for item in _items(row) if item.objectName() in ("contextPreviewLabel", "contextPreviewDetail") and item.isVisible()]
            for label in labels:
                assert label.property("contentHeight") <= label.height() + 1
                assert label.mapToItem(row, QPointF(0, label.height())).y() <= row.height()
            if len(labels) == 2:
                assert labels[0].mapToScene(QPointF(0, labels[0].height())).y() <= labels[1].mapToScene(QPointF()).y()
        assert all(a.y() + a.height() <= b.y() for a, b in zip(rows, rows[1:]))
        assert dialog.property("height") <= window.height()
        button_name = "confirmInterviewAnswerContext" if property_name == "aiPreview" else "confirmInterviewSetupContext"
        button = _find(window, button_name)
        background = dialog.property("background")
        assert button.mapToItem(background, QPointF(0, button.height())).y() <= background.height() - 12
        _capture(window, f"context-{property_name}-{size[0]}-dark-1.25")
        listing.setProperty("contentY", max(0, listing.property("contentHeight") - listing.height()))
        QTest.qWait(50)
        last = rows[-1]
        bottom = last.mapToItem(listing, QPointF(0, last.height())).y()
        assert bottom <= listing.height() + 1, "The complete material row must be reachable by scrolling"
        QMetaObject.invokeMethod(dialog, "reject")
        QTest.qWait(150)


def test_interview_session_details_and_reconfigure_preserve_results(scene):
    window, controller = scene
    _click(window, _find(window, "openInterviewSessionInfo"))
    dialog = window.findChild(QObject, "interviewSessionInfoDialog")
    assert dialog.property("visible")
    assert "实习" in dialog.property("message")
    QMetaObject.invokeMethod(dialog, "accept")
    QTest.qWait(150)
    controller.finishInterview()
    QTest.qWait(100)
    previous_id = controller.interview["interview_id"]
    assert _find(window, "interviewConversation").isVisible()
    _click(window, _find(window, "configureAnotherInterview"))
    assert _find(window, "interviewRoleSelector").isVisible()
    back = next(item for item in _items(window.contentItem()) if item.isVisible() and item.property("text") == "返回上一场结果" and hasattr(item, "clicked"))
    back.clicked.emit()
    QTest.qWait(50)
    assert _find(window, "interviewConversation").isVisible()
    assert controller.interview["interview_id"] == previous_id


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_shell_setup_home_coach_and_settings_have_readable_controls(scene, theme):
    window, controller = scene
    window.resize(1280, 800)
    window.setProperty("displayFontScaleOverride", 1.0)
    controller.setTheme(theme)
    for page_id in ("home", "coach", "settings"):
        controller.navigate(page_id)
        QTest.qWait(150)
        if page_id == "coach":
            editor = _find(window, "coachPrompt")
            _click(window, editor)
            QCoreApplication.sendEvent(editor, QInputMethodEvent("zhong", []))
            assert not _visible_hints(editor)
            event = QInputMethodEvent()
            event.setCommitString("这是用于检查中文输入的合成文本")
            QCoreApplication.sendEvent(editor, event)
            assert not _visible_hints(editor)
            assert editor.property("cursorRectangle").y() >= editor.property("topPadding") - 1
        title = _find(window, "shellRouteTitle")
        assert title.width() > 0 and title.height() >= title.property("contentHeight") - 1
        _capture(window, f"{page_id}-1280x800-{theme}")
    controller.navigate("interview")
    controller.finishInterview()
    QTest.qWait(80)
    _click(window, _find(window, "configureAnotherInterview"))
    selector = _find(window, "interviewAiModeSelector")
    selector.setProperty("currentIndex", 2)
    for size in ((900, 620), (1280, 800)):
        window.resize(*size)
        window.setProperty("displayFontScaleOverride", 1.25 if size[0] == 900 else 1.0)
        QTest.qWait(100)
        start = _find(window, "startConfiguredInterview")
        pos = start.mapToScene(QPointF())
        assert start.isVisible() and start.isEnabled()
        assert pos.y() >= 0 and pos.y() + start.height() <= window.height()
        assert pos.x() >= 0 and pos.x() + start.width() <= window.width()
        _capture(window, f"setup-{size[0]}x{size[1]}-{theme}")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_small_home_and_coach_keep_text_inside_controls(scene, theme):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    controller.setTheme(theme)
    controller.navigate("home")
    QTest.qWait(100)
    _capture(window, f"home-900x620-{theme}-1.25")
    for name in ("homeTodayFocus", "homeEvidenceRail"):
        card = _find(window, name)
        for item in _items(card):
            if item.isVisible() and item.property("text") and item.property("contentHeight") is not None:
                assert item.property("contentHeight") <= item.height() + 1, item.property("text")
                assert item.mapToItem(card, QPointF(0, item.height())).y() <= card.height(), item.property("text")
    controller.navigate("coach")
    QTest.qWait(100)
    start = _find(window, "coachEmptyStart")
    assert start.property("resolvedBackground") != start.property("resolvedForeground")
    editor = _find(window, "coachPrompt")
    _click(window, editor)
    QCoreApplication.sendEvent(editor, QInputMethodEvent("zhong", []))
    assert not _visible_hints(editor)
    event = QInputMethodEvent()
    event.setCommitString("放大字体和窄窗口下的中文输入检查")
    QCoreApplication.sendEvent(editor, event)
    assert editor.property("cursorRectangle").bottom() < editor.height()
    send = _find(window, "sendCoachTurn")
    assert send.mapToScene(QPointF(0, send.height())).y() <= window.height()
    _capture(window, f"coach-900x620-{theme}-1.25")
