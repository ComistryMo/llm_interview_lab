"""Targeted regression tests for the first-run role-selection hotfix."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QPoint, QPointF, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import AppController


REPO_ROOT = Path(__file__).resolve().parents[2]
QML_PATH = REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml"
ROLE_IDS = (
    "ai_product_manager",
    "applied_ai_engineer",
    "ai_agent_engineer",
    "ai_algorithm_research_engineer",
    "post_training_engineer",
    "ai_infra_engineer",
    "ai_inference_systems_engineer",
    "ai_evaluation_data_safety_engineer",
)


@pytest.fixture(scope="module")
def qapp() -> QGuiApplication:
    return QGuiApplication.instance() or QGuiApplication(["onboarding-hotfix-tests"])


def _descendants(item: QQuickItem):
    for child in item.childItems():
        yield child
        yield from _descendants(child)


@pytest.fixture
def onboarding_scene(qapp: QGuiApplication):
    controller = AppController(REPO_ROOT, demo_page="onboarding")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    assert engine.rootObjects(), "Main.qml did not create a window"
    window = engine.rootObjects()[0]
    window.show()
    page = window.findChild(QQuickItem, "onboardingPage")
    assert page is not None, "onboarding page was not created"
    page.setProperty("step", 1)
    for _ in range(4):
        QCoreApplication.processEvents()
    scene = (qapp, window, page)
    yield scene
    window.close()
    engine.deleteLater()
    controller.shutdown()
    QCoreApplication.processEvents()


def _role_cards(scene) -> list[QQuickItem]:
    _, _, page = scene
    grid = page.findChild(QQuickItem, "onboardingRoleGrid")
    assert grid is not None
    cards = [
        item
        for item in _descendants(grid)
        if item.objectName().startswith("onboardingRoleCard-")
    ]
    return sorted(cards, key=lambda item: int(item.property("index")))


def _click_item(window, item: QQuickItem) -> None:
    point = item.mapToItem(None, QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(
        window,
        Qt.MouseButton.LeftButton,
        pos=QPoint(round(point.x()), round(point.y())),
    )
    QCoreApplication.processEvents()


def test_onboarding_uses_explicit_grid_geometry_and_no_index_default() -> None:
    source = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/OnboardingPage.qml"
    ).read_text(encoding="utf-8")
    assert "GridView" in source
    assert "GridLayout {" not in source
    assert 'property string selectedRole: ""' in source
    assert "app.roles[3]" not in source
    assert 'objectName: "onboardingRoleGrid"' in source
    assert 'objectName: "onboardingContinueButton"' in source


def test_role_cards_have_positive_non_overlapping_geometry(onboarding_scene) -> None:
    _, _, page = onboarding_scene
    grid = page.findChild(QQuickItem, "onboardingRoleGrid")
    cards = _role_cards(onboarding_scene)
    assert grid is not None
    assert len(cards) == len(ROLE_IDS)
    assert grid.width() >= 760

    for card in cards:
        assert 92 <= card.height() <= 108
        assert card.width() > 0
        assert card.height() > 0

    for first_index, first in enumerate(cards):
        for second in cards[first_index + 1 :]:
            same_row = abs(first.y() - second.y()) < 1
            same_column = abs(first.x() - second.x()) < 1
            if same_row:
                assert (
                    first.x() + first.width() <= second.x()
                    or second.x() + second.width() <= first.x()
                )
            if same_column:
                assert (
                    first.y() + first.height() <= second.y()
                    or second.y() + second.height() <= first.y()
                )


@pytest.mark.parametrize("index", [0, 3, 7])
def test_clicking_first_fourth_and_eighth_roles_selects_id(onboarding_scene, index: int) -> None:
    _, window, page = onboarding_scene
    card = _role_cards(onboarding_scene)[index]
    _click_item(window, card)
    assert page.property("selectedRole") == ROLE_IDS[index]
    label = page.findChild(QQuickItem, "onboardingSelectedRoleLabel")
    marker = next(
        (
            item
            for item in _descendants(page)
            if item.objectName() == f"onboardingRoleSelected-{ROLE_IDS[index]}"
        ),
        None,
    )
    assert label is not None and ROLE_IDS[index] not in str(label.property("text"))
    assert marker is not None and marker.property("visible") is True


def test_next_is_disabled_until_a_role_is_selected(onboarding_scene) -> None:
    _, window, page = onboarding_scene
    page.setProperty("selectedRole", "")
    QCoreApplication.processEvents()
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert button is not None
    assert button.property("enabled") is False
    _click_item(window, button)
    assert page.property("step") == 1


def test_main_toast_is_top_right_and_named() -> None:
    source = (REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml").read_text(
        encoding="utf-8"
    )
    assert 'objectName: "globalToast"' in source
    assert "y: 82" in source
