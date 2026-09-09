"""Geometry of the production choice controls, including wrapped Chinese labels."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtGui import QFontMetricsF, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.mark.parametrize("scale", [1.0, 1.25])
@pytest.mark.parametrize("control_type", ["LabCheckBox", "LabSwitch"])
def test_choice_indicator_tracks_label_and_control_center(control_type, scale):
    app = QGuiApplication.instance() or QApplication(["choice-alignment"])
    engine = QQmlApplicationEngine()
    root = Path(__file__).resolve().parents[2] / "src/llm_interview_lab/desktop/qml"
    source = '''
import QtQuick
import "components"
Window {
    width: 420; height: 360; visible: true
    AppTheme { id: appTheme; fontScale: SCALE; uiFontFamily: "Microsoft YaHei UI" }
    Column {
        width: 400; spacing: 12
        CONTROL { objectName: "normal"; theme: appTheme; text: "允许使用材料" }
        CONTROL {
            objectName: "compact"; theme: appTheme; text: "每轮附带已授权的简历 / JD"
            font.pixelSize: appTheme.fontCaption; height: appTheme.controlHeightCompact
        }
        CONTROL {
            objectName: "wrapped"; theme: appTheme; width: 180
            text: "允许本场面试使用所选简历和岗位描述材料"
        }
    }
}
'''.replace("CONTROL", control_type).replace("SCALE", str(scale))
    engine.loadData(source.encode(), QUrl.fromLocalFile(str(root / "ChoiceAlignment.qml")))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    try:
        QTest.qWait(80)
        for name in ("normal", "compact", "wrapped"):
            control = window.findChild(QObject, name)
            label = control.property("contentItem")
            indicator = control.property("indicator")
            metrics = QFontMetricsF(control.property("font"))
            center = indicator.y() + indicator.height() / 2
            first_line_center = label.y() + label.property("baselineOffset") - metrics.ascent() + metrics.height() / 2
            assert abs(center - first_line_center) <= 1, (name, center, first_line_center)
            if name != "wrapped":
                assert abs(center - control.height() / 2) <= 1, (name, center, control.height())
            else:
                assert label.property("lineCount") > 1
                assert control.height() >= label.property("contentHeight") + 16
            assert indicator.y() >= 0 and indicator.y() + indicator.height() <= control.height()
    finally:
        window.close()
        engine.deleteLater()
        QCoreApplication.sendPostedEvents()
        app.processEvents()
