"""Targeted regression tests for the first-run role-selection hotfix."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
# Match the production entry point.  Loading the same Material style keeps the
# fixture from emitting native-style customization warnings that production lacks.
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")
pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QPoint, QPointF, QSettings, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.workspace import profile_paths


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


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    for name in ("pyproject.toml", ".gitignore"):
        shutil.copy2(REPO_ROOT / name, root / name)
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


@pytest.fixture(scope="module")
def qml_repository(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _repository(tmp_path_factory.mktemp("onboarding-qml"))


@pytest.fixture
def onboarding_scene(qapp: QGuiApplication, qml_repository: Path, tmp_path: Path):
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    controller = AppController(qml_repository, demo_page="onboarding")
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
    scene = (qapp, window, page, controller)
    yield scene
    window.close()
    engine.deleteLater()
    controller.shutdown()
    QCoreApplication.processEvents()


def _role_cards(scene) -> list[QQuickItem]:
    _, _, page, _ = scene
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
    assert "app.onboardingBusy" in source
    assert "Qt.callLater" in source
    assert 'objectName: "onboardingRoleGrid"' in source
    assert 'objectName: "onboardingContinueButton"' in source
    assert "policy: roleGrid.interactive" in source
    assert "ScrollBar.AsNeeded" in source
    assert 'readonly property bool wideLayout: width >= 1180' in source
    assert "roleGrid.currentIndex = i" in source
    assert "property int stepCount: 2" in source
    assert "Layout.preferredWidth: root.step >= 1 ? 144 : 112" in source


def test_role_cards_have_positive_non_overlapping_geometry(onboarding_scene) -> None:
    _, _, page, _ = onboarding_scene
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


def test_supported_small_window_uses_one_reliable_role_column(onboarding_scene) -> None:
    _, window, page, _ = onboarding_scene
    window.resize(1080, 680)
    for _ in range(4):
        QCoreApplication.processEvents()
    grid = page.findChild(QQuickItem, "onboardingRoleGrid")
    assert grid is not None
    assert grid.property("columnCount") == 1
    cards = _role_cards(onboarding_scene)
    assert cards
    assert all(card.width() > 0 and 92 <= card.height() <= 108 for card in cards)


@pytest.mark.parametrize("index", [0, 3, 7])
def test_clicking_first_fourth_and_eighth_roles_selects_id(onboarding_scene, index: int) -> None:
    _, window, page, _ = onboarding_scene
    grid = page.findChild(QQuickItem, "onboardingRoleGrid")
    assert grid is not None
    card = _role_cards(onboarding_scene)[index]
    # The eighth card is below the initial viewport.  Scroll the real GridView
    # before clicking so this test verifies hit testing, not an off-screen item.
    if card.y() + card.height() > grid.property("contentY") + grid.height():
        grid.setProperty(
            "contentY",
            max(0.0, card.y() - grid.height() + card.height() + 4),
        )
        QCoreApplication.processEvents()
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
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert button is not None
    assert button.property("enabled") is True
    assert button.width() >= 112
    assert button.height() >= 40


def test_next_is_disabled_until_a_role_is_selected(onboarding_scene) -> None:
    _, window, page, _ = onboarding_scene
    page.setProperty("selectedRole", "")
    QCoreApplication.processEvents()
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert button is not None
    assert button.property("enabled") is False
    _click_item(window, button)
    assert page.property("step") == 1


def test_submit_state_is_visible_and_blocks_repeat_clicks(onboarding_scene) -> None:
    _, _, page, _ = onboarding_scene
    page.setProperty("step", 1)
    page.setProperty("selectedRole", ROLE_IDS[0])
    page.setProperty("submitting", True)
    QCoreApplication.processEvents()
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert button is not None
    assert button.property("text") == "正在创建…"
    assert button.property("enabled") is False


def test_inline_error_stays_above_the_primary_action(onboarding_scene) -> None:
    _, _, page, _ = onboarding_scene
    page.setProperty("inlineError", "创建学习档案失败，请根据提示检查输入后重试。")
    QCoreApplication.processEvents()
    panel = page.findChild(QQuickItem, "onboardingInlineError")
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert panel is not None and panel.property("visible") is True
    assert button is not None
    panel_bottom = panel.mapToItem(page, QPointF(0, panel.height())).y()
    button_top = button.mapToItem(page, QPointF(0, 0)).y()
    assert panel_bottom <= button_top


def test_no_ai_first_run_reaches_the_first_exercise(onboarding_scene) -> None:
    _, window, page, controller = onboarding_scene
    profile_name = page.findChild(QQuickItem, "onboardingProfileName")
    button = page.findChild(QQuickItem, "onboardingContinueButton")
    assert profile_name is not None and button is not None
    profile_name.setProperty("text", "hotfix-user")

    page.setProperty("step", 0)
    QCoreApplication.processEvents()
    _click_item(window, button)
    assert page.property("step") == 1
    _click_item(window, _role_cards(onboarding_scene)[4])
    _click_item(window, button)

    for _ in range(30):
        if controller.currentPage == "exercise":
            break
        QTest.qWait(100)
    assert controller.currentPage == "exercise"
    assert controller.currentTask["problem_id"] == "FND-001"
    assert profile_paths(controller.repo_root, "hotfix-user").profile_file.is_file()


def test_main_toast_is_top_right_and_named() -> None:
    source = (REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml").read_text(
        encoding="utf-8"
    )
    assert 'objectName: "globalToast"' in source
    assert "codexApprovalBanner.visible" in source
    assert "codexApprovalBanner.y + codexApprovalBanner.height + 10" in source
    assert ": 82" in source


def test_fresh_exercise_qml_keeps_unreviewed_practice_actionable(
    qapp: QGuiApplication,
) -> None:
    controller = AppController(REPO_ROOT, demo_page="exercise")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    window.show()
    for _ in range(4):
        QCoreApplication.processEvents()
    button = window.findChild(QQuickItem, "practicePrimaryAction")
    assert button is not None
    assert button.property("visible") is True
    assert button.property("text") == "运行公开测试"

    controller.runTests()
    for _ in range(4):
        QCoreApplication.processEvents()
    assert button.property("visible") is True
    assert button.property("text") == "提交实现"
    window.close()
    engine.deleteLater()
    controller.shutdown()
    QCoreApplication.processEvents()
