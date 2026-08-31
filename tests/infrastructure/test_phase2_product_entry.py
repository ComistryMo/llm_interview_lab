"""Focused Phase 2 product-entry contracts.

These tests intentionally stay at the Profile/shell boundary.  They do not
exercise the full curriculum or provider matrix.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication

from llm_interview_lab.application import ApplicationService
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.workspace import profile_paths, profile_summaries


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp():
    application = QGuiApplication.instance() or QGuiApplication(["phase2-entry"])
    yield application


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    shutil.copy2(REPO_ROOT / "pyproject.toml", root / "pyproject.toml")
    shutil.copy2(REPO_ROOT / ".gitignore", root / ".gitignore")
    shutil.copytree(REPO_ROOT / "curriculum", root / "curriculum")
    shutil.copytree(REPO_ROOT / "workspace/schema", root / "workspace/schema")
    shutil.copytree(REPO_ROOT / "workspace/templates", root / "workspace/templates")
    profiles = root / "workspace/profiles"
    profiles.mkdir(parents=True)
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _settings(tmp_path: Path) -> None:
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))


def _active_key(root: Path) -> str:
    digest = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"profiles/{digest}/active_profile_id"


def test_profile_switcher_is_metadata_only_and_switches_isolated_snapshots(
    tmp_path: Path, qapp
) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("alpha-user", display_name="Alpha 档案")
    service.initialize_profile("beta-user", display_name="Beta 档案")

    summaries = profile_summaries(root)
    assert {item["profile_id"] for item in summaries} == {"alpha-user", "beta-user"}
    assert all(set(item) == {
        "profile_id", "display_name", "status", "error_code", "role_id", "seniority"
    } for item in summaries)

    controller = AppController(root, profile_id="alpha-user")
    assert controller.profileDisplayName == "Alpha 档案"
    assert controller.switchProfile("beta-user") is True
    assert controller.profileId == "beta-user"
    assert controller.profileDisplayName == "Beta 档案"

    controller.updateSubmissionDraft("unsaved text")
    # There is no active attempt in this fixture, so explicitly model a dirty
    # editor snapshot to verify the switch gate without creating a submission.
    controller._submission_saved_revision = "saved-revision"
    assert controller.switchProfile("alpha-user") is False
    assert controller.lastActionResult["error_code"] == "UNSAVED_CHANGES"
    assert controller.profileId == "beta-user"
    controller.shutdown()


def test_profile_switch_clears_pending_ai_assessment(tmp_path: Path, qapp) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("alpha-user")
    service.initialize_profile("beta-user")
    controller = AppController(root, profile_id="alpha-user")
    controller._pending_ai_assessment = {
        "profile_id": "alpha-user",
        "interview_id": "interview-alpha",
        "question_id": "question-alpha",
    }

    assert controller.switchProfile("beta-user") is True
    assert controller._pending_ai_assessment is None
    assert controller.profileId == "beta-user"
    controller.shutdown()


def test_last_profile_missing_is_explicit_not_silently_recreated(tmp_path: Path, qapp) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    settings = QSettings("ComistryMo", "LLMInterviewLab")
    settings.setValue(_active_key(root), "deleted-profile")
    settings.sync()

    controller = AppController(root, profile_id="default")
    assert controller.onboardingRequired is True
    assert controller.profileRestoreErrorCode == "PROFILE_NOT_FOUND"
    assert "没有找到" in controller.profileRestoreError
    assert not profile_paths(root, "deleted-profile").root.exists()
    controller.shutdown()


def test_corrupt_last_profile_is_explicit(tmp_path: Path, qapp) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    ApplicationService(root).initialize_profile("broken-user", display_name="损坏档案")
    profile_file = profile_paths(root, "broken-user").profile_file
    profile_file.write_text("not: [valid", encoding="utf-8")
    settings = QSettings("ComistryMo", "LLMInterviewLab")
    settings.setValue(_active_key(root), "broken-user")
    settings.sync()

    controller = AppController(root, profile_id="default")
    assert controller.onboardingRequired is True
    assert controller.profileRestoreErrorCode == "PROFILE_CORRUPTED"
    assert "无法读取" in controller.profileRestoreError
    controller.shutdown()


def test_language_setting_persists_between_desktop_launches(tmp_path: Path, qapp) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    ApplicationService(root).initialize_profile("language-user", display_name="语言档案")

    first = AppController(root, profile_id="language-user")
    assert first.language == "zh-CN"
    first.setLanguage("en")
    assert first.language == "en"
    first.shutdown()

    reopened = AppController(root, profile_id="language-user")
    assert reopened.language == "en"
    assert reopened.uiText("nav.home") == "Home"
    reopened.setLanguage("zh-CN")
    reopened.shutdown()


def test_no_ai_interview_is_a_truthful_lock_page() -> None:
    source = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml"
    ).read_text(encoding="utf-8")
    assert 'objectName: "noAiInterviewLockPanel"' in source
    assert 'objectName: "goToConnectionsFromInterview"' in source
    assert 'objectName: "continueNoAiPractice"' in source
    assert "不会创建虚假的 Session、评分或报告" in source
    assert "app.navigate(\"connections\")" in source
    assert "app.navigate(\"learn\")" in source


def test_phase2_shell_contracts_are_explicit() -> None:
    settings = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/SettingsPage.qml"
    ).read_text(encoding="utf-8")
    onboarding = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/OnboardingPage.qml"
    ).read_text(encoding="utf-8")
    assert 'objectName: "profileSwitcher"' in settings
    assert 'objectName: "codexDiscoveryStatus"' in settings
    assert "app.setLanguage(modelData.id)" in settings
    assert "app.profileRestoreError" in onboarding
    assert "root.submitting || app.onboardingBusy" in onboarding
    assert 'objectName: "onboardingErrorAction"' in onboarding
    assert 'objectName: "onboardingErrorCode"' in onboarding


def test_open_problem_failure_has_actionable_structured_result(
    tmp_path: Path, qapp
) -> None:
    del qapp
    _settings(tmp_path)
    root = _repository(tmp_path)
    ApplicationService(root).initialize_profile("entry-user")
    controller = AppController(root, profile_id="entry-user")
    messages: list[str] = []
    controller.toast.connect(messages.append)

    assert controller.openProblem("not-a-real-problem") is False
    result = controller.lastActionResult
    assert result["success"] is False
    assert result["error_code"]
    assert result["user_message"]
    assert result["recommended_action"]
    assert result["operation_id"]
    assert messages and "错误编号：" in messages[-1]
    assert "操作未完成" not in messages[-1]
    controller.shutdown()
