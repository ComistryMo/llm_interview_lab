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
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        for theme in ("light", "dark"):
            controller.setTheme(theme)
            for scale in (1.0, 1.25):
                window.setProperty("displayFontScaleOverride", scale)
                QTest.qWait(60)
                editor = _find(window, "interviewCodingEditor")
                toggle = _find(window, "toggleInterviewCodingPrompt")
                if width < 1180 and not editor.isVisible():
                    _click(window, toggle)
                    QTest.qWait(30)
                assert editor.isVisible() and editor.width() > 300
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
                if (width, scale) == (1280, 1.0):
                    _capture(window, f"unified-coding-{theme}")
