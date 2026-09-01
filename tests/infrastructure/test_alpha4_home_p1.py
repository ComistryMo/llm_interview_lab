from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.events import AttemptState, WorkspaceState, append_event
from llm_interview_lab.workspace import event_schema_path, profile_paths


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Material")

pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_QML = (
    REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/HomePage.qml"
)
T0 = datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='alpha4-home-fixture'\nversion='0'\n", encoding="utf-8"
    )
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n", encoding="utf-8"
    )
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    (root / "workspace/profiles").mkdir(parents=True)
    (root / "workspace/profiles/.gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _mark_reviewed(
    service: ApplicationService, profile_id: str, problem_id: str
) -> None:
    service.start_practice(profile_id, problem_id)
    current = service.current_submission(profile_id)
    assert current is not None
    paths = profile_paths(service.repo_root, profile_id)
    append_event(
        paths.events_file,
        event_schema_path(service.repo_root),
        profile_id=profile_id,
        event_type="task_implemented",
        problem_id=problem_id,
        attempt_id=current["attempt_id"],
        payload={"submission_sha256": current["sha256"]},
        timestamp=T0,
    )
    append_event(
        paths.events_file,
        event_schema_path(service.repo_root),
        profile_id=profile_id,
        event_type="review_completed",
        problem_id=problem_id,
        attempt_id=current["attempt_id"],
        payload={
            "submission_sha256": current["sha256"],
            "contract_status": "passed",
            "oral_status": "passed",
            "code_explanation": "Synthetic explanation for a local test profile.",
            "complexity": "O(n).",
            "boundary_conditions": "Empty and invalid inputs are explicit.",
        },
        timestamp=T0,
    )


def _home_component(dashboard: dict, *, width: int = 900, height: int = 620):
    pytest.importorskip("PySide6")
    from PySide6.QtCore import QCoreApplication, QObject, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    application = QGuiApplication.instance() or QGuiApplication(["alpha4-home-p1"])
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(HOME_QML)))
    assert component.isReady(), [error.toString() for error in component.errors()]
    root = component.createWithInitialProperties(
        {
            "app": {
                "dashboard": dashboard,
                "interview": {},
                "recentInterview": {},
            },
            "palette": {
                "text": "#171717",
                "surface": "#fbfaf7",
                "border": "#dedbd3",
                "accent": "#315ec7",
                "warning": "#9a6700",
                "danger": "#b42318",
                "success": "#16794a",
            },
            "width": width,
            "height": height,
        }
    )
    assert root is not None, [error.toString() for error in component.errors()]
    QQmlEngine.setObjectOwnership(root, QQmlEngine.CppOwnership)
    for _ in range(4):
        QCoreApplication.processEvents()
    evidence = root.findChild(QObject, "homeEvidenceRail")
    content = root.findChild(QObject, "homeEvidenceContent")
    assert evidence is not None
    assert content is not None
    return application, engine, component, root, evidence, content


def test_due_d2_replaces_reviewed_current_attempt_as_home_focus(tmp_path: Path) -> None:
    service = ApplicationService(_repository(tmp_path))
    service.initialize_profile("reviewed-user", role_id="applied_ai_engineer")
    _mark_reviewed(service, "reviewed-user", "FND-001")

    dashboard = service.dashboard("reviewed-user", now=T0 + timedelta(days=2))
    assert dashboard["current"]["status"] == "reviewed"
    assert dashboard["due_retention"][0]["stage"] == "d2"

    _application, engine, _component, root, _evidence, _content = _home_component(
        dashboard
    )
    assert root.property("focusKind") == "retention"
    root.deleteLater()
    engine.deleteLater()


def test_due_d7_replaces_retained_d2_current_attempt_as_home_focus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ApplicationService(_repository(tmp_path))
    service.initialize_profile("retained-user", role_id="applied_ai_engineer")
    paths, profile, _original_state = service._state("retained-user")
    attempt_id = "attempt-reviewed-0001"
    state = WorkspaceState(
        profile_id="retained-user",
        current_problem_id="FND-001",
        current_attempt_id=attempt_id,
    )
    state.attempts[("FND-001", attempt_id)] = AttemptState(
        problem_id="FND-001",
        attempt_id=attempt_id,
        implemented=True,
        reviewed=True,
    )
    state.reviewed_at["FND-001"] = T0
    state.retained_d2.add("FND-001")
    monkeypatch.setattr(
        service, "_state", lambda profile_id: (paths, profile, state)
    )

    dashboard = service.dashboard("retained-user", now=T0 + timedelta(days=7))
    assert dashboard["current"]["status"] == "retained_d2"
    assert dashboard["due_retention"][0]["stage"] == "d7"

    _application, engine, _component, root, _evidence, _content = _home_component(
        dashboard
    )
    assert root.property("focusKind") == "retention"
    root.deleteLater()
    engine.deleteLater()


def test_dashboard_counts_all_due_items_while_preview_remains_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = ApplicationService(_repository(tmp_path))
    service.initialize_profile("count-user", role_id="applied_ai_engineer")
    paths, profile, _original_state = service._state("count-user")
    state = WorkspaceState(profile_id="count-user")

    reviewed_problem_ids = ("FND-001", "FND-002", "FND-003", "FND-004")
    for index, problem_id in enumerate(reviewed_problem_ids, start=1):
        attempt_id = f"attempt-reviewed-{index:04d}"
        state.attempts[(problem_id, attempt_id)] = AttemptState(
            problem_id=problem_id,
            attempt_id=attempt_id,
            implemented=True,
            reviewed=True,
        )
        state.reviewed_at[problem_id] = T0

    for index, problem_id in enumerate(
        ("LOSS-007", "LOSS-008", "LOSS-013", "LOSS-014"), start=1
    ):
        attempt_id = f"attempt-review-due-{index:04d}"
        state.attempts[(problem_id, attempt_id)] = AttemptState(
            problem_id=problem_id,
            attempt_id=attempt_id,
            implemented=True,
            reviewed=False,
        )

    state.current_problem_id = "FND-001"
    state.current_attempt_id = "attempt-reviewed-0001"
    monkeypatch.setattr(
        service, "_state", lambda profile_id: (paths, profile, state)
    )

    dashboard = service.dashboard("count-user", now=T0 + timedelta(days=2))
    assert dashboard["due_review_count"] == 4
    assert dashboard["due_retention_count"] == 4
    assert len(dashboard["due_review"]) == 3
    assert len(dashboard["due_retention"]) == 3


def test_compact_evidence_rail_grows_to_fit_its_content() -> None:
    dashboard = {
        "current": None,
        "due_review": ["FND-001", "FND-002", "FND-003"],
        "due_review_count": 12,
        "due_retention": [],
        "due_retention_count": 9,
        "unlocks": [],
        "mastered_count": 27,
        "role": {
            "primary_role": "llm_vlm_post_training_engineer",
            "title": "LLM/VLM Post-Training Engineer",
            "seniority": "new_grad",
        },
    }
    _application, engine, _component, root, evidence, content = _home_component(
        dashboard
    )

    padding = float(evidence.property("padding"))
    assert float(evidence.property("width")) > 0
    assert float(evidence.property("height")) >= float(
        content.property("implicitHeight")
    ) + 2 * padding
    assert float(root.property("contentHeight")) > float(root.property("height"))
    assert float(evidence.property("y")) + float(evidence.property("height")) <= (
        float(root.property("contentHeight")) + 1.0
    )
    assert int(root.property("dueReviewCount")) == 12
    assert int(root.property("dueRetentionCount")) == 9
    root.deleteLater()
    engine.deleteLater()


def test_standard_home_keeps_learning_evidence_beside_focus_card() -> None:
    dashboard = {
        "current": None,
        "due_review": [],
        "due_review_count": 2,
        "due_retention": [],
        "due_retention_count": 1,
        "unlocks": [],
        "mastered_count": 3,
        "role": {
            "primary_role": "llm_vlm_post_training_engineer",
            "title": "LLM/VLM Post-Training Engineer",
            "seniority": "new_grad",
        },
    }
    _application, engine, _component, root, evidence, _content = _home_component(
        dashboard, width=1180, height=800
    )

    from PySide6.QtCore import QObject

    focus = root.findChild(QObject, "homeTodayFocus")
    grid = root.findChild(QObject, "homeOverviewGrid")
    assert focus is not None
    assert grid is not None
    assert float(focus.property("width")) > float(evidence.property("width")) > 0
    assert float(evidence.property("y")) == pytest.approx(
        float(focus.property("y")), abs=1.0
    )
    assert float(evidence.property("x")) > float(focus.property("x"))
    assert float(evidence.property("x")) + float(evidence.property("width")) <= (
        float(grid.property("width")) + 1.0
    )
    root.deleteLater()
    engine.deleteLater()
