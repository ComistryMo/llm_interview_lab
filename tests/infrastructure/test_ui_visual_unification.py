"""Presentation-only acceptance using the real controller and production QML."""
import os
import re
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QUrl, Qt, QMetaObject, QObject, QSettings
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from tests.infrastructure.test_interview_input_runtime import (
    qapp, public_repo, controller, _find, _click, _capture, _enter_coding_round,
    _within_window, _items, QML,
)


@pytest.fixture
def scene(controller):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(v.toString() for v in values))
    engine.rootContext().setContextProperty("backend", controller)
    # Optional read-only historical worktree for Before screenshots, never a
    # prototype or alternate controller. No real Profile or service is opened.
    source = Path(os.environ.get("LLM_LAB_UI_QML_BASELINE", str(QML)))
    engine.load(QUrl.fromLocalFile(str(source)))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.show()
    QTest.qWait(80)
    yield window, controller
    assert not warnings, "\n".join(warnings)
    window.close()
    engine.deleteLater()
    QCoreApplication.processEvents()


def test_theme_text_and_focus_contrast(scene):
    window, app = scene
    theme = next(item for item in window.findChildren(QObject)
                 if item.metaObject().className().startswith("AppTheme_QML"))

    def luminance(color):
        channels = (color.redF(), color.greenF(), color.blueF())
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    def ratio(first, second):
        light, dark = sorted((luminance(first), luminance(second)), reverse=True)
        return (light + 0.05) / (dark + 0.05)

    for mode in ("light", "dark"):
        app.setTheme(mode)
        QCoreApplication.processEvents()
        for surface in ("canvas", "chrome", "surface", "surfaceRaised", "surfaceSunken", "surfaceHover"):
            for ink in ("textStrong", "text", "muted", "subtle"):
                assert ratio(theme.property(ink), theme.property(surface)) >= 4.5, (mode, ink, surface)
            assert ratio(theme.property("focusRing"), theme.property(surface)) >= 3.0


def test_fresh_onboarding_at_all_display_modes(qapp, public_repo, tmp_path, monkeypatch):
    from llm_interview_lab.desktop.controller import AppController

    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings",
                        lambda *args: QSettings(str(tmp_path / "first-run.ini"), QSettings.IniFormat))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    app = AppController(public_repo)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda values: errors.extend(v.toString() for v in values))
    engine.rootContext().setContextProperty("backend", app)
    engine.load(QUrl.fromLocalFile(str(QML)))
    assert engine.rootObjects(), errors
    window = engine.rootObjects()[0]
    try:
        window.show()
        page = _find(window, "onboardingPage")
        assert page.isVisible()
        page.setProperty("step", 1)
        for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
            window.resize(width, height)
            for mode in ("light", "dark"):
                app.setTheme(mode)
                for scale in (1.0, 1.25):
                    window.setProperty("displayFontScaleOverride", scale)
                    QTest.qWait(40)
                    assert _within_window(window, _find(window, "onboardingContinueButton"))
                    summary = _find(window, "onboardingSelectionSummary")
                    assert _within_window(window, summary)
                    grid = _find(window, "onboardingRoleGrid")
                    assert grid.height() > 100
                    for card in _items(grid):
                        if not card.objectName().startswith("onboardingRoleCard-"):
                            continue
                        for label in _items(card):
                            if label.property("contentHeight") is not None and label.isVisible():
                                assert label.property("contentHeight") <= label.height() + 1
                    if (width, scale) == (1280, 1.0):
                        _capture(window, f"onboarding-{mode}")
        assert not errors, errors
    finally:
        window.close()
        engine.deleteLater()
        app.shutdown()
        QCoreApplication.processEvents()


def test_refresh_confirmation_fits_large_text(scene):
    window, app = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    app.navigate("settings")
    dialog = _find(window, "refreshDirtyDraftDialog")
    QMetaObject.invokeMethod(dialog, "open", Qt.DirectConnection)
    QTest.qWait(60)
    assert dialog.property("height") <= window.height()
    body = dialog.property("contentItem")
    for item in _items(body):
        if item.property("contentHeight") is not None:
            assert item.property("contentHeight") <= item.height() + 1
    QMetaObject.invokeMethod(dialog, "reject", Qt.DirectConnection)
    assert not dialog.property("visible")
    QCoreApplication.processEvents()


def test_markdown_headings_use_the_scaled_section_token(scene):
    _, app = scene
    rendered = app.renderMarkdown("# 标题\n\n## 接口\n\n中文正文\n\n```python\nprint(1)\n```", 23, "Cascadia Mono")
    assert len(re.findall(r'<h[12] style="font-size:23px;', rendered)) == 2
    assert "中文正文" in rendered and "print(1)" in rendered
    assert "white-space:pre-wrap" in rendered


def test_visible_coding_workspace_runs_real_script_and_keeps_draft(scene):
    window, app = scene
    window.resize(1280, 800)
    _enter_coding_round(app)
    editor = _find(window, "interviewCodingEditor")
    script = "# 合成 UI 验收，不是本题答案\nprint(sum([2, 3, 4]))\n"
    editor.setProperty("text", script)
    _click(window, _find(window, "runInterviewScript"))
    deadline = time.monotonic() + 15
    while app.busy and time.monotonic() < deadline:
        QTest.qWait(30)
        time.sleep(0.005)
    assert not app.busy
    result = app.interview["coding_run"]
    assert result["exit_code"] == 0 and result["stdout"] == "9\n"
    assert "9" in _find(window, "interviewCodingOutput").property("text")
    assert editor.property("text") == script
    assert _find(window, "submitInterviewCode").isEnabled()
    assert app.interview.get("coding_test_status") != "passed"


def test_connection_error_remains_below_fields_and_retryable(scene):
    window, app = scene
    window.resize(900, 620)
    window.setProperty("displayFontScaleOverride", 1.25)
    app.navigate("connections")
    QTest.qWait(60)
    _click(window, _find(window, "saveAndTestConnection"))
    error = _find(window, "connectionFormError")
    assert error.isVisible() and error.property("text")
    assert not app.busy and not app.connections
    assert _find(window, "saveAndTestConnection").isEnabled()
    page = _find(window, "connectionsPage")
    for theme in ("light", "dark"):
        app.setTheme(theme)
        page.setProperty("contentY", max(0, page.property("contentHeight") - page.height()))
        QTest.qWait(50)
        assert error.property("contentHeight") <= error.height() + 1
        assert _within_window(window, error)
        _capture(window, f"connection-error-900-125-{theme}")


@pytest.mark.parametrize("page", ["home", "setup", "answer", "coding", "report", "connections", "settings"])
def test_production_page_gallery(scene, page):
    window, app = scene
    window.resize(1280, 800)
    if page == "coding":
        _enter_coding_round(app)
        QTest.qWait(100)
        # Read the beginning of the real prompt for the comparison capture.
        # This is a viewport operation, not a synthetic editor or product change.
        _find(window, "interviewQuestionScroll").property("contentItem").setProperty("contentY", 0)
    elif page == "report":
        app.lockInterviewAnswer("合成验收：我负责构造独立验证集，比较训练前后的错误类型。没有真实个人资料。")
        app.finishInterview()
    elif page == "setup":
        app.finishInterview()
        app.prepareInterview()
    elif page == "answer":
        _find(window, "interviewAnswerEditor").setProperty("text", "合成验收草稿：我负责训练数据去重和验证集划分，并用独立样本检查模型泛化。")
    else:
        app.navigate(page)
    for theme in ("light", "dark"):
        app.setTheme(theme)
        QTest.qWait(90)
        if page == "report":
            report = _find(window, "interviewResultCard")
            _find(window, "interviewQuestionScroll").property("contentItem").setProperty("contentY", report.y())
        _capture(window, f"{page}-{theme}")


@pytest.mark.parametrize("page", ["home", "learn", "progress", "career", "connections", "settings"])
def test_page_text_and_controls_fit_all_display_modes(scene, page):
    window, app = scene
    app.navigate(page)
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        window.resize(width, height)
        for theme in ("light", "dark"):
            app.setTheme(theme)
            for scale in (1.0, 1.25):
                window.setProperty("displayFontScaleOverride", scale)
                QTest.qWait(35)
                for item in _items(window.contentItem()):
                    if not item.isVisible() or item.width() <= 0 or not _within_window(window, item):
                        continue
                    kind = item.metaObject().className()
                    if kind.startswith(("LabText_QML", "LabCheckBox_QML")):
                        content_height = item.property("contentHeight")
                        if content_height is not None:
                            assert content_height <= item.height() + 2, (page, width, scale, item.objectName(), item.property("text"))
                    if kind.startswith(("LabTextField_QML", "LabComboBox_QML", "LabButton_QML")):
                        assert item.height() >= 39, (page, width, scale, kind, item.objectName())


def test_shared_controls_keep_native_input_and_dialog_contracts(qapp):
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda values: errors.extend(v.toString() for v in values))
    controls = QUrl.fromLocalFile(str(QML.parent / "components")).toString()
    engine.loadData(f'''
import QtQuick
import QtQuick.Controls
import "{controls}"
ApplicationWindow {{
    width: 480; height: 620; visible: true
    AppTheme {{ id: testTheme; fontScale: 1.25; uiFontFamily: "Microsoft YaHei UI" }}
    Column {{
        x: 24; y: 24; width: 420; spacing: 16
        LabTextField {{ objectName: "field"; theme: theme; width: parent.width; placeholderText: "输入中文名称" }}
        LabComboBox {{ objectName: "combo"; theme: theme; width: parent.width; model: ["标准", "困难"] }}
        LabCheckBox {{ objectName: "consent"; theme: theme; width: 230; text: "允许本场面试使用明确授权的简历与岗位材料，不包含其他材料" }}
        LabSwitch {{ objectName: "switch"; theme: theme; text: "开关" }}
        LabSpinBox {{ objectName: "spin"; theme: theme; from: 1; to: 150; value: 60; stepSize: 5; editable: true }}
        LabTabButton {{ objectName: "tab"; theme: theme; text: "准备面试" }}
        LabButton {{ objectName: "action"; theme: theme; text: "确认"; highlighted: true }}
    }}
    LabStandardDialog {{ objectName: "dialog"; theme: theme; title: "确认操作"; width: 360; standardButtons: Dialog.Cancel | Dialog.Ok }}
}}
'''.replace("theme: theme", "theme: testTheme").encode())
    assert engine.rootObjects(), errors
    window = engine.rootObjects()[0]
    QTest.qWait(60)
    for name in ("field", "combo", "spin", "action"):
        assert _find(window, name).height() >= 40
    consent = _find(window, "consent")
    assert consent.height() > 60
    _click(window, consent)
    assert consent.property("checked")
    switch = _find(window, "switch")
    _click(window, switch)
    assert switch.property("checked")
    spin = _find(window, "spin")
    spin.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Up)
    assert spin.property("value") == 65
    action = _find(window, "action")
    assert action.property("variant") == "primary"
    dialog = _find(window, "dialog")
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    QMetaObject.invokeMethod(dialog, "open", Qt.DirectConnection)
    QTest.qWait(50)
    buttons = [i for i in _items(window.contentItem()) if i.isVisible()
               and str(i.property("text") or "").replace("&", "") in ("OK", "确定")
               and i.metaObject().className().startswith("LabButton_QML")]
    assert buttons, [(i.metaObject().className(), i.property("text")) for i in _items(window.contentItem()) if i.isVisible() and i.property("text")]
    _click(window, buttons[0])
    assert accepted and not dialog.property("visible")
    assert not errors, errors
    window.close()
    engine.deleteLater()
