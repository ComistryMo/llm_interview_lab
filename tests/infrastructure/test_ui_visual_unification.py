"""Presentation-only acceptance using the real controller and production QML."""
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QUrl, Qt, QMetaObject
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


@pytest.mark.parametrize("page", ["home", "setup", "answer", "coding", "report", "connections", "settings"])
def test_production_page_gallery(scene, page):
    window, app = scene
    window.resize(1280, 800)
    if page == "coding":
        _enter_coding_round(app)
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
