from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication

from llm_interview_lab.application import ApplicationError, ApplicationService
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.roles import RoleCatalogError
from llm_interview_lab.workspace import load_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp():
    application = QGuiApplication.instance() or QGuiApplication(["onboarding-hotfix"])
    yield application


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='onboarding-hotfix'\nversion='0'\n", encoding="utf-8"
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


def _controller(tmp_path: Path, qapp) -> AppController:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(
        QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings")
    )
    return AppController(_repository(tmp_path), profile_id="default")


@pytest.mark.parametrize(
    ("profile_id", "role_id", "seniority", "ai_mode", "assessment", "error"),
    [
        ("bad-seniority", "post_training_engineer", "staff", "disabled", {}, ApplicationError),
        ("bad-ai", "post_training_engineer", "new_grad", "unknown", {}, ApplicationError),
        ("bad-role", "missing-role", "new_grad", "disabled", {}, RoleCatalogError),
        ("bad-skill", "post_training_engineer", "new_grad", "disabled", {"missing.skill": 2}, ApplicationError),
    ],
)
def test_application_prevalidates_role_configuration_before_profile_write(
    tmp_path: Path,
    profile_id: str,
    role_id: str,
    seniority: str,
    ai_mode: str,
    assessment: dict[str, int],
    error: type[Exception],
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)

    with pytest.raises(error):
        service.initialize_profile(
            profile_id,
            role_id=role_id,
            seniority=seniority,
            ai_mode=ai_mode,
            skill_self_assessment=assessment,
        )

    assert not profile_paths(root, profile_id).root.exists()


def test_clean_no_ai_onboarding_enters_first_problem_and_can_resume(
    tmp_path: Path, qapp
) -> None:
    controller = _controller(tmp_path, qapp)

    assert controller.completeOnboarding(
        "first-user", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    assert not controller.onboardingRequired
    assert controller.currentPage == "exercise"
    assert controller.currentTask["problem_id"] == "FND-001"
    assert controller.onboardingError == ""

    assert controller.completeOnboarding(
        "first-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    profile = load_profile(profile_paths(controller.repo_root, "first-user"), controller.repo_root)
    assert profile["role_preferences"]["primary_role"] == "ai_product_manager"
    controller.shutdown()


def test_default_desktop_restart_restores_the_last_profile(
    tmp_path: Path, qapp
) -> None:
    """A packaged-style launch with the implicit default id keeps its Profile."""

    root = _repository(tmp_path)
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(
        QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings")
    )

    first = AppController(root, profile_id="default")
    assert first.completeOnboardingWithDisplayName(
        "中文后训练准备", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    created_id = first.profileId
    assert created_id != "default"
    assert first.profileDisplayName == "中文后训练准备"
    first.shutdown()

    reopened = AppController(root, profile_id="default")
    assert reopened.profileId == created_id
    assert reopened.activeProfileId == created_id
    assert reopened.profileDisplayName == "中文后训练准备"
    assert reopened.onboardingRequired is False
    reopened.shutdown()


@pytest.mark.parametrize(
    ("profile_id", "role_id", "seniority", "ai_mode", "assessment", "code"),
    [
        ("中文 档案", "post_training_engineer", "new_grad", "disabled", "{}", "PROFILE_ID_INVALID"),
        ("valid-user", "", "new_grad", "disabled", "{}", "ROLE_REQUIRED"),
        ("valid-user", "missing-role", "new_grad", "disabled", "{}", "ROLE_NOT_FOUND"),
        ("valid-user", "post_training_engineer", "staff", "disabled", "{}", "SENIORITY_UNSUPPORTED"),
        ("valid-user", "post_training_engineer", "new_grad", "unknown", "{}", "AI_MODE_INVALID"),
        ("valid-user", "post_training_engineer", "new_grad", "disabled", "[1]", "ASSESSMENT_INVALID"),
    ],
)
def test_onboarding_input_failures_are_specific_and_do_not_write_profile(
    tmp_path: Path,
    qapp,
    profile_id: str,
    role_id: str,
    seniority: str,
    ai_mode: str,
    assessment: str,
    code: str,
) -> None:
    controller = _controller(tmp_path, qapp)

    assert not controller.completeOnboarding(
        profile_id, role_id, seniority, ai_mode, assessment
    )
    assert controller.onboardingErrorCode == code
    assert controller.onboardingError
    if profile_id == "valid-user":
        assert not profile_paths(controller.repo_root, profile_id).root.exists()
    controller.shutdown()


def test_onboarding_guard_blocks_repeated_initialization(tmp_path: Path, qapp) -> None:
    controller = _controller(tmp_path, qapp)
    controller._onboarding_busy = True

    assert not controller.completeOnboarding(
        "repeat-user", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    assert not profile_paths(controller.repo_root, "repeat-user").root.exists()
    controller._onboarding_busy = False
    controller.shutdown()


def test_onboarding_without_unlocks_finishes_on_home(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _controller(tmp_path, qapp)
    real_dashboard = controller.service.dashboard

    def no_unlocks(profile_id: str):
        value = real_dashboard(profile_id)
        return {**value, "unlocks": []}

    monkeypatch.setattr(controller.service, "dashboard", no_unlocks)

    assert controller.completeOnboarding(
        "no-unlock-user", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    assert controller.currentPage == "home"
    assert not controller.onboardingRequired
    controller.shutdown()


def test_first_problem_failure_falls_back_to_home_after_profile_creation(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller = _controller(tmp_path, qapp)
    messages: list[str] = []
    controller.toast.connect(messages.append)

    def fail_open(_: str) -> None:
        raise RuntimeError("synthetic open failure")

    monkeypatch.setattr(controller, "_open_problem", fail_open)
    assert controller.completeOnboarding(
        "open-fallback", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    assert profile_paths(controller.repo_root, "open-fallback").profile_file.is_file()
    assert not controller.onboardingRequired
    assert controller.currentPage == "home"
    assert messages == [
        "学习档案已创建，但首题暂时无法打开。请从首页进入刷题训练重试；若仍失败，请打开日志目录。（错误编号：INTERNAL_ERROR）"
    ]
    assert controller.lastActionResult["error_code"] == "INTERNAL_ERROR"
    assert controller.lastActionResult["recommended_action"]
    controller.shutdown()


def test_unknown_onboarding_failure_is_logged_and_exposes_stable_code(
    tmp_path: Path,
    qapp,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    controller = _controller(tmp_path, qapp)

    def fail_initialize(*args, **kwargs):
        del args, kwargs
        raise RuntimeError(f"synthetic failure at {controller.repo_root}")

    monkeypatch.setattr(controller.service, "initialize_profile", fail_initialize)
    caplog.set_level(logging.ERROR, logger="llm_interview_lab.desktop")

    assert not controller.completeOnboarding(
        "unknown-user", "post_training_engineer", "new_grad", "disabled", "{}"
    )
    assert controller.onboardingErrorCode == "ONBOARDING_UNEXPECTED"
    assert "stage=initialize_profile" in caplog.text
    assert "error_type=RuntimeError" in caplog.text
    assert str(controller.repo_root) not in caplog.text
    controller.shutdown()
