"""New discovery and update controls exercised on the real QML shell."""
from tests.infrastructure.test_interview_input_runtime import qapp, public_repo, controller, scene, _find, _click, _wait_for_asr, _within_window, _capture

from PySide6.QtCore import Q_ARG, QMetaObject, QPointF, Qt
from PySide6.QtTest import QTest

from llm_interview_lab.desktop import updates
from tests.infrastructure.test_desktop_updates import selected


def variant(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


def reveal(item, window):
    QTest.qWait(60)  # Complete the real page's queued layout after navigation.
    parent = item.parentItem()
    while parent:
        if parent.property("contentY") is not None:
            y = item.mapToItem(parent, QPointF()).y() + parent.property("contentY")
            parent.setProperty("contentY", min(max(0, y - 80), max(0, parent.property("contentHeight") - parent.height())))
            QTest.qWait(50)
            break
        parent = parent.parentItem()


def test_difficulty_and_environment_filters_preserve_verified_eligibility(scene):
    window, controller = scene
    controller.navigate("learn")
    page = _find(window, "learnPage")
    page.setProperty("filterMode", "verified")
    QMetaObject.invokeMethod(page, "refreshList")
    original = variant(page.property("filteredProblems"))
    expected = [row for row in controller.problems if row["asset_status"] != "planned" and row["validation"] in {"oracle", "field", "stable"}]
    assert {row["problem_id"] for row in original} == {row["problem_id"] for row in expected}
    assert len(original) > 0
    assert all(row["asset_status"] != "planned" and row["validation"] in {"oracle", "field", "stable"} for row in original)
    for level in range(1, 6):
        difficulty = _find(window, "learnCodingLevel")
        difficulty.setProperty("currentIndex", level)
        QMetaObject.invokeMethod(difficulty, "activated", Qt.DirectConnection, Q_ARG(int, level))
        QTest.qWait(20)
        found = variant(page.property("filteredProblems"))
        assert found == [row for row in original if row["difficulty"]["coding"] == level]
    difficulty.setProperty("currentIndex", 0)
    QMetaObject.invokeMethod(difficulty, "activated", Qt.DirectConnection, Q_ARG(int, 0))
    environment = _find(window, "learnEnvironmentFilter")
    environment.setProperty("currentIndex", 1)
    QMetaObject.invokeMethod(environment, "activated", Qt.DirectConnection, Q_ARG(int, 1))
    QTest.qWait(20)
    assert variant(page.property("filteredProblems")) == [row for row in original if row["environment_available"]]
    _capture(window, "candidate-discovery")


def test_real_settings_update_controls_resize_and_retry(scene, monkeypatch):
    window, controller = scene
    controller.navigate("settings")
    manager = controller.updateManager
    monkeypatch.setattr(updates, "check_releases", lambda *args: (_ for _ in ()).throw(updates.UpdateError("合成网络失败，请重试。")))
    button = _find(window, "checkDesktopUpdate")
    reveal(button, window)
    assert _within_window(window, button), (button.mapToScene(QPointF()), button.width(), button.height())
    _click(window, button)
    assert _wait_for_asr(lambda: manager.state["status"] == "error")
    assert "合成网络失败" in _find(window, "updateStatus").property("text")
    monkeypatch.setattr(updates, "check_releases", lambda *args: {**selected(), "notes": "合成更新说明；不执行安装。\n" * 25})
    _click(window, button)
    assert _wait_for_asr(lambda: manager.state["status"] == "available")
    download = _find(window, "downloadDesktopUpdate")
    for width, height in ((900, 620), (1080, 680), (1280, 800), (1440, 900)):
        for theme in ("light", "dark"):
            for scale in (1.0, 1.25):
                controller.setTheme(theme)
                window.resize(width, height)
                window.setProperty("displayFontScaleOverride", scale)
                QTest.qWait(30)
                reveal(download, window)
                assert _within_window(window, download)
                assert download.height() >= 40
                assert _find(window, "updateStatus").property("implicitHeight") > 0
    _capture(window, "candidate-update-settings")


def test_existing_keyboard_navigation_is_not_a_header_search_field(scene):
    window, controller = scene
    controller.navigate("home")
    QTest.keyClick(window, Qt.Key_K, Qt.ControlModifier)
    QTest.qWait(80)
    search = _find(window, "commandPaletteSearch")
    assert search.property("visible")
    search.setProperty("text", "设置")
    search.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Return)
    QTest.qWait(40)
    assert controller.currentPage == "settings"
