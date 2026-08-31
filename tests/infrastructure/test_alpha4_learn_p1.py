"""Focused Material-style runtime coverage for the Alpha 4 Learn surface."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QPoint, QPointF, QSettings, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import AppController


REPO_ROOT = Path(__file__).resolve().parents[2]
QML_PATH = REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml"


@pytest.fixture(scope="module")
def qapp(tmp_path_factory: pytest.TempPathFactory) -> QGuiApplication:
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(
        QSettings.IniFormat,
        QSettings.UserScope,
        str(tmp_path_factory.mktemp("alpha4-learn-settings")),
    )
    return QGuiApplication.instance() or QGuiApplication(["alpha4-learn-p1-tests"])


def _settle(iterations: int = 8) -> None:
    for _ in range(iterations):
        QCoreApplication.processEvents()


def _descendants(item: QQuickItem):
    for child in item.childItems():
        yield child
        yield from _descendants(child)


def _find_prefix(item: QQuickItem, prefix: str) -> QQuickItem:
    match = next(
        (child for child in _descendants(item) if child.objectName().startswith(prefix)),
        None,
    )
    assert match is not None, f"missing QML item with objectName prefix {prefix!r}"
    return match


def _click(window: QQuickItem, item: QQuickItem) -> None:
    point = item.mapToItem(None, QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(point.x()), round(point.y())),
    )
    _settle()


@contextmanager
def _learn_scene(
    qapp: QGuiApplication,
    *,
    width: int,
    height: int,
    font_scale: float = 1.0,
):
    controller = AppController(REPO_ROOT, demo_page="learn")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    assert engine.rootObjects(), "Main.qml did not create a window"
    window = engine.rootObjects()[0]
    window.resize(width, height)
    window.setProperty("displayFontScaleOverride", font_scale)
    window.show()
    _settle()
    page = window.findChild(QQuickItem, "learnPage")
    assert page is not None and page.property("visible") is True
    try:
        yield window, page, controller
    finally:
        window.close()
        engine.deleteLater()
        controller.shutdown()
        _settle(2)


@pytest.mark.parametrize(
    ("width", "height", "layout_mode"),
    [(900, 620, "compact"), (1280, 800, "standard")],
)
def test_course_list_drills_into_detail_and_back(
    qapp: QGuiApplication,
    width: int,
    height: int,
    layout_mode: str,
) -> None:
    with _learn_scene(qapp, width=width, height=height) as (window, page, _):
        assert page.property("layoutMode") == layout_mode
        row = _find_prefix(page, "learnProblemRow-")
        assert row.property("visible") is True

        _click(window, row)
        assert page.property("compactDetail") is True
        back = page.findChild(QQuickItem, "learnCourseBackButton")
        assert back is not None and back.property("visible") is True

        _click(window, back)
        assert page.property("compactDetail") is False
        assert row.property("visible") is True


def test_knowledge_detail_wraps_without_horizontal_overflow_at_140_percent(
    qapp: QGuiApplication,
) -> None:
    with _learn_scene(
        qapp, width=900, height=620, font_scale=1.4
    ) as (window, page, controller):
        _click(window, page.findChild(QQuickItem, "knowledgeBrowserButton"))
        assert controller.knowledgeLoaded is True
        row = _find_prefix(page, "knowledgeRow-")
        _click(window, row)
        assert page.property("compactKnowledgeDetail") is True

        scroll = page.findChild(QQuickItem, "knowledgeDetailScroll")
        content = page.findChild(QQuickItem, "knowledgeDetailContent")
        source = page.findChild(QQuickItem, "knowledgeSourceText")
        assert scroll is not None and scroll.property("visible") is True
        assert content is not None and source is not None
        available_width = float(scroll.property("availableWidth"))
        assert available_width > 0
        assert float(scroll.property("contentWidth")) <= available_width + 1
        assert content.width() <= available_width + 1
        assert float(source.property("contentWidth")) <= source.width() + 1
        assert float(scroll.property("contentHeight")) > float(
            scroll.property("availableHeight")
        ), "140% knowledge detail must remain vertically scrollable"

        back = page.findChild(QQuickItem, "knowledgeBackButton")
        assert back is not None and back.property("visible") is True
        _click(window, back)
        assert page.property("compactKnowledgeDetail") is False


def test_knowledge_load_failure_keeps_retry_action_and_recovers(
    qapp: QGuiApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _learn_scene(qapp, width=900, height=620) as (window, page, controller):
        original = controller.service.knowledge_cards
        attempts = 0

        def fail_once(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            raise RuntimeError("synthetic knowledge load failure")

        monkeypatch.setattr(controller.service, "knowledge_cards", fail_once)
        _click(window, page.findChild(QQuickItem, "knowledgeBrowserButton"))
        assert attempts == 1
        assert controller.knowledgeLoaded is False
        empty = page.findChild(QQuickItem, "knowledgeEmptyState")
        retry = page.findChild(QQuickItem, "knowledgeRetryButton")
        assert empty is not None and empty.property("visible") is True
        assert retry is not None and retry.property("visible") is True
        assert "刷新" in str(retry.property("text"))

        monkeypatch.setattr(controller.service, "knowledge_cards", original)
        _click(window, retry)
        assert controller.knowledgeLoaded is True
        knowledge_list = page.findChild(QQuickItem, "knowledgeCardList")
        assert knowledge_list is not None
        assert int(knowledge_list.property("count")) > 0
