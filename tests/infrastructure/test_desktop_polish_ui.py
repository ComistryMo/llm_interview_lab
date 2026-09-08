"""Scoped production-page UX checks with isolated Profiles and microphone fixtures."""

from __future__ import annotations

import time

import pytest

from .test_interview_input_runtime import (
    QCoreApplication, QPointF, QTest, Qt,
    _capture, _click, _dictation_model_ready, _find, _stub_dictation_capture,
    _within_window,
)
from .test_interview_input_runtime import controller as controller
from .test_interview_input_runtime import public_repo as public_repo
from .test_interview_input_runtime import qapp as qapp
from .test_interview_input_runtime import scene as scene


SIZES = [
    ((900, 620), "dark", 1.25),
    ((1080, 680), "light", 1.0),
    ((1280, 800), "dark", 1.0),
    ((1440, 900), "light", 1.0),
]


@pytest.mark.parametrize("size,theme,scale", SIZES)
def test_dictation_status_stays_beside_composer(scene, monkeypatch, size, theme, scale):
    window, controller = scene
    controller.setTheme(theme)
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", scale)
    _dictation_model_ready(controller, monkeypatch)
    _stub_dictation_capture(controller, monkeypatch)
    def stream(blocks, update, cancel):
        # The production path is streaming; don't accidentally load the real
        # decoder through an obsolete batch-transcribe mock in a UI test.
        for _ in blocks:
            pass
        return "合成语音：我负责独立评估。"
    monkeypatch.setattr(controller._local_stt, "stream", stream)
    QTest.qWait(100)
    editor = _find(window, "interviewAnswerEditor")
    editor.setProperty("text", "保留我写的回答。")
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    reading_position = viewport.property("contentY")
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(50)
    assert controller.interviewVoice["state"] == "recording"
    controller._voice_recorder._duration_changed(2300)
    QCoreApplication.processEvents()
    status = _find(window, "interviewVoiceCard")
    stop = _find(window, "finishInterviewDictation")
    composer = _find(window, "interviewPhaseGuidance")
    assert status.height() <= 54 * scale
    assert _within_window(window, status) and _within_window(window, stop)
    assert status.mapToScene(QPointF(0, status.height())).y() <= composer.mapToScene(QPointF()).y()
    assert viewport.property("contentY") == reading_position
    assert _find(window, "interviewVoiceDuration").property("text") == "0:02"
    assert not _find(window, "lockInterviewAnswer").isEnabled()
    _capture(window, f"polish-voice-recording-{size[0]}-{theme}")
    _click(window, stop)
    for _ in range(120):
        QTest.qWait(20)
        time.sleep(.005)
        if controller.interviewVoice["transcription_state"] == "transcribed":
            break
    assert controller.interviewVoice["transcription_state"] == "transcribed"
    assert editor.property("text") == "保留我写的回答。\n合成语音：我负责独立评估。"
    assert not controller.interview["answer_locked"]
    assert not stop.isVisible()
    assert status.height() <= 54 * scale
    _capture(window, f"polish-voice-draft-{size[0]}-{theme}")


@pytest.mark.parametrize("size,theme,scale", SIZES)
def test_setup_ai_summary_and_compact_appearance(scene, size, theme, scale):
    window, controller = scene
    controller.setTheme(theme)
    window.resize(*size)
    window.setProperty("displayFontScaleOverride", scale)
    controller.finishInterview()
    QTest.qWait(60)
    _click(window, _find(window, "configureAnotherInterview"))
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 2)
    QTest.qWait(80)
    summary = _find(window, "interviewSetupAiSummary")
    assert "Codex" in summary.property("text") and "尚未发现" in summary.property("text")
    assert _within_window(window, summary)
    assert _within_window(window, _find(window, "interviewSetupConnectionShortcut"))
    assert _within_window(window, _find(window, "startConfiguredInterview"))
    assert not _find(window, "interviewUseMaterials").property("checked")
    _capture(window, f"polish-setup-{size[0]}-{theme}")
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 0)
    QCoreApplication.processEvents()
    assert "需连接" in summary.property("text")
    assert not _find(window, "startConfiguredInterview").isVisible()
    _click(window, _find(window, "interviewSetupConnectionShortcut"))
    assert controller.currentPage == "connections"

    controller.navigate("settings")
    card = _find(window, "settingsAppearanceCard")
    # StackLayout polishes the formerly hidden page on a scheduled frame.
    # macOS CI observed its transient 36 px implicit width at a fixed 80 ms.
    # Wait for actual geometry, retaining all size and real-click assertions.
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        QTest.qWait(20)
        if (_within_window(window, card) and card.height() < 250 * scale
                and abs(card.width() - card.parentItem().width()) <= 1):
            break
    assert _within_window(window, card), (card.size(), card.mapToScene(QPointF()))
    assert abs(card.width() - card.parentItem().width()) <= 1
    assert card.height() < 250 * scale
    assert _find(window, "settingsFontScale").width() <= 280
    _click(window, _find(window, "settingsTheme-light" if theme == "dark" else "settingsTheme-dark"))
    assert controller.theme == ("light" if theme == "dark" else "dark")
    _click(window, _find(window, "settingsLanguage-en"))
    assert controller.language == "en"
    _click(window, _find(window, "settingsLanguage-zh-CN"))
    assert controller.language == "zh-CN"
    controller.setTheme(theme)
    _capture(window, f"polish-settings-{size[0]}-{theme}")


def test_voice_advanced_options_scroll_without_moving_question(scene, monkeypatch):
    window, controller = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    monkeypatch.setattr(controller._local_stt, "ready", lambda: False)
    monkeypatch.setattr(controller._local_stt, "runtime_available", lambda: True)
    controller._refresh_local_stt_status()
    controller.stateChanged.emit()
    QTest.qWait(80)
    viewport = _find(window, "interviewQuestionScroll").property("contentItem")
    reading_position = viewport.property("contentY")
    _click(window, _find(window, "toggleInterviewVoice"))
    QTest.qWait(80)
    assert controller.interviewVoice["state"] != "recording"
    assert viewport.property("contentY") == reading_position
    assert _find(window, "interviewVoiceSettingsScroll").isVisible()
    assert _within_window(window, _find(window, "startInterviewRecordingFromSettings"))
    assert not _find(window, "startInterviewRecordingFromSettings").isEnabled()
    assert _find(window, "downloadLocalSttModel").isVisible()
    assert not _find(window, "interviewVoiceRemoteConsent").property("checked")
    _capture(window, "polish-voice-settings-900-dark")
    _click(window, _find(window, "closeInterviewVoiceSettings"))
    assert not controller.busy


def test_model_settings_links_scroll_to_editable_codex_fields(scene):
    window, controller = scene
    window.resize(900, 620)
    controller.navigate("connections")
    QTest.qWait(80)
    page = _find(window, "connectionsPage")
    entry = _find(window, "openCodexModelSettings")
    page.setProperty("contentY", max(0, entry.mapToItem(page, QPointF()).y() - 140))
    QTest.qWait(60)
    _click(window, entry)
    QTest.qWait(100)
    assert controller.currentPage == "settings"
    model = _find(window, "codexModelField")
    assert _within_window(window, model) and model.hasActiveFocus(), (
        model.mapToScene(QPointF()), model.size(),
        _find(window, "settingsPage").property("contentY"),
        _find(window, "settingsPage").property("contentHeight"), model.hasActiveFocus(),
    )
    # Exercise native editing: setProperty would remove the QML text binding
    # and conceal resets caused by the controller's coarse stateChanged.
    for key in (Qt.Key_M, Qt.Key_O, Qt.Key_D, Qt.Key_E, Qt.Key_L):
        QTest.keyClick(window, key)
    assert model.property("text") == "model"
    effort = _find(window, "codexReasoningEffort")
    effort.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_End)
    assert effort.property("currentValue") == "xhigh"
    model.forceActiveFocus()
    controller.stateChanged.emit()
    controller.setTheme("light" if controller.theme == "dark" else "dark")
    controller.interviewTranscriptReady.emit("合成后台转录，不抢设置输入焦点。")
    QCoreApplication.processEvents()
    assert model.hasActiveFocus() and model.property("text") == "model"
    assert effort.property("currentValue") == "xhigh"
    assert controller.codexModel == "" and controller.codexReasoningEffort == ""
    QTest.keyClick(window, Qt.Key_X)
    assert model.property("text") == "modelx"
    assert "合成后台转录" in _find(window, "interviewAnswerEditor").property("text")
    _click(window, _find(window, "saveCodexModelPreferences"))
    assert controller.codexModel == "modelx" and controller.codexReasoningEffort == "xhigh"
    controller.stateChanged.emit()
    QCoreApplication.processEvents()
    assert model.property("text") == "modelx" and effort.property("currentValue") == "xhigh"
    _capture(window, "polish-codex-settings-link-900")
    controller.navigate("interview")
    controller.finishInterview()
    QTest.qWait(60)
    _click(window, _find(window, "configureAnotherInterview"))
    _click(window, _find(window, "interviewEditSettings"))
    _find(window, "interviewAiModeSelector").setProperty("currentIndex", 2)
    QTest.qWait(80)
    entry = _find(window, "openCodexPreferencesFromInterview")
    viewport = _find(window, "interviewSetupScroll").property("contentItem")
    viewport.setProperty("contentY", max(0, entry.mapToItem(viewport, QPointF()).y() - 100))
    QTest.qWait(60)
    _click(window, entry)
    QTest.qWait(80)
    assert controller.currentPage == "settings"
    assert _within_window(window, model) and model.hasActiveFocus()
