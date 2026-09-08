"""Production QML acceptance for role-only preparation and the shared editor."""
import pytest
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest

from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, scene, _find, _click, _within_window,
    _capture, _enter_coding_round,
)


def test_unified_setup_home_history_at_all_sizes(scene):
    window, controller = scene
    controller.finishInterview()
    assert controller.interview["status"] == "incomplete"
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        for theme in ("light", "dark"):
            controller.setTheme(theme)
            for scale in (1.0, 1.25):
                window.setProperty("displayFontScaleOverride", scale)
                controller.prepareInterview()
                QTest.qWait(60)
                assert not window.findChild(QObject, "interviewSenioritySelector")
                edit = _find(window, "interviewEditSettings")
                assert edit.isVisible() and _within_window(window, edit)
                start = _find(window, "startConfiguredInterview")
                assert _within_window(window, start)
                assert "seniority" not in controller.interviewPreferences()
                _click(window, edit)
                QTest.qWait(40)
                for name in ("interviewDifficultySelector", "interviewDurationSelector"):
                    field = _find(window, name)
                    assert field.width() > 110 and field.height() >= 40
                    assert _within_window(window, field)
                _click(window, edit)
                controller.navigate("home")
                QTest.qWait(40)
                action = _find(window, "homePrimaryAction")
                assert action.property("text") == "开始面试"
                assert action.isVisible() and _within_window(window, action)
                for name in ("homeFocusTitle", "homeEvidenceNote"):
                    label = _find(window, name)
                    assert label.property("contentHeight") <= label.height() + 1
                if (width, scale) == (1280, 1.0):
                    _capture(window, f"unified-home-{theme}")
                    controller.prepareInterview()
                    QTest.qWait(50)
                    _capture(window, f"unified-setup-{theme}")
    controller.showInterviewHistory()
    QTest.qWait(60)
    assert len(controller.interviewHistory()) == 1


def test_coding_workspace_keeps_one_editor_and_actions(scene):
    window, controller = scene
    _enter_coding_round(controller)
    original_editor = _find(window, "interviewCodingEditor")
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        for theme in ("light", "dark"):
            controller.setTheme(theme)
            for scale in (1.0, 1.25):
                window.setProperty("displayFontScaleOverride", scale)
                QTest.qWait(60)
                editor = _find(window, "interviewCodingEditor")
                assert editor is original_editor
                toggle = _find(window, "toggleInterviewCodingPrompt")
                if width < 1180 and not editor.isVisible():
                    _click(window, toggle)
                    QTest.qWait(30)
                assert editor.isVisible() and editor.width() > 300
                prompt = _find(window, "interviewQuestionPrompt")
                assert prompt.property("contentWidth") <= prompt.width() + 1
                history = _find(window, "interviewCodingHistory")
                title = _find(window, "interviewQuestionTitle")
                assert title.y() >= history.y() + history.height()
                for name in ("runInterviewScript", "runInterviewGrader", "submitInterviewCode"):
                    button = _find(window, name)
                    assert button.isVisible() and _within_window(window, button), (width, scale, name)
                expected = "# 中文注释\ndef attention(x):\n    return x\n\nprint(attention([1, 2]))"
                editor.setProperty("text", expected)
                _click(window, editor)
                QTest.keyClick(window, Qt.Key_End, Qt.ControlModifier)
                QTest.keyClick(window, Qt.Key_Return)
                QTest.keyClick(window, Qt.Key_Tab)
                assert editor.property("text").endswith("\n    ")
                assert "中文注释" in editor.property("text")
                if width >= 1180:
                    # Geometry alone cannot catch a reparented editor culled
                    # by its previous viewport. Verify it is actually painted.
                    QTest.qWait(30)
                    shot = window.grabWindow()
                    point = editor.mapToScene(QPointF(editor.width() - 24, editor.height() - 24))
                    painted = shot.pixelColor(round(point.x() * shot.width() / window.width()),
                                              round(point.y() * shot.height() / window.height()))
                    assert painted.name() == editor.property("theme").property("surface").name()
                else:
                    draft = editor.property("text")
                    _click(window, toggle)
                    _click(window, toggle)
                    assert editor.property("text") == draft
                if (width, scale) == (1280, 1.0):
                    _capture(window, f"unified-coding-{theme}")


def test_report_gap_links_open_actual_knowledge_and_fit_scaled_windows(scene):
    window, controller = scene
    controller.lockInterviewAnswer("合成验收：我负责公开模型的独立评测集，没有真实个人信息。")
    controller.finishInterview()
    assert controller.interview["result"]["learning_gaps"]
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        for theme in ("light", "dark"):
            controller.setTheme(theme)
            for scale in (1.0, 1.25):
                window.setProperty("displayFontScaleOverride", scale)
                QTest.qWait(65)
                report = _find(window, "interviewResultCard")
                assert report.width() <= window.width()
                score = _find(window, "interviewResultScore")
                assert score.property("font").pixelSize() <= int(18 * scale + .5)
                if (width, scale) == (1280, 1.0):
                    scroll = _find(window, "interviewQuestionScroll")
                    scroll.property("contentItem").setProperty("contentY", report.y())
                    _capture(window, f"unified-report-{theme}")
    card_id = controller.interview["result"]["learning_gaps"][0]["knowledge"][0]["id"]
    button = _find(window, "reportKnowledge-" + card_id)
    # Invoke the real QML action even when its row requires scrolling.
    from PySide6.QtCore import QMetaObject
    QMetaObject.invokeMethod(button, "clicked", Qt.DirectConnection)
    QTest.qWait(120)
    assert controller.currentPage == "learn"
    assert controller.knowledgeDetail["id"] == card_id
