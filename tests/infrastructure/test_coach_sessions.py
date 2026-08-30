"""Targeted contracts for the profile-local desktop Coach workspace."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import threading

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QSettings

from llm_interview_lab.coach_sessions import (
    CoachSessionError,
    coach_sessions_path,
    load_coach_sessions,
    message as coach_message,
    new_coach_session,
    write_coach_sessions,
)
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.workspace import init_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp():
    application = QGuiApplication.instance() or QGuiApplication(["coach-tests"])
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


def _profile(root: Path, profile_id: str) -> None:
    init_profile(root, profile_id)


def test_session_store_roundtrip_is_atomic_and_profile_scoped(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    _profile(root, "alpha-user")
    _profile(root, "beta-user")

    created = new_coach_session(
        root,
        "alpha-user",
        mode="teacher",
        provider_kind="none",
        problem_id="FND-001",
        title="Shape 复盘",
    )
    created["messages"].append(coach_message("user", "只讨论当前题面"))
    write_coach_sessions(root, "alpha-user", [created])

    path = coach_sessions_path(root, "alpha-user")
    assert path == profile_paths(root, "alpha-user").coach_root / "sessions.json"
    assert path.is_file()
    assert load_coach_sessions(root, "alpha-user")[0]["mode"] == "teacher"
    assert load_coach_sessions(root, "beta-user") == []
    assert "api_key" not in path.read_text(encoding="utf-8").lower()
    assert not list(path.parent.glob("*.tmp"))


def test_malformed_store_is_rejected_without_falling_back_to_another_profile(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    _profile(root, "alpha-user")
    _profile(root, "beta-user")
    alpha_path = coach_sessions_path(root, "alpha-user")
    alpha_path.parent.mkdir(parents=True, exist_ok=True)
    alpha_path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(CoachSessionError):
        load_coach_sessions(root, "alpha-user")
    assert load_coach_sessions(root, "beta-user") == []


def test_controller_no_ai_turn_persists_and_never_changes_practice_state(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="coach-user")
    assert controller.completeOnboarding(
        "coach-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    before_submission = controller.submissionText
    before_events = profile_paths(root, "coach-user").events_file.read_text(encoding="utf-8")

    assert controller.createCoachSession("coach", "none", "", "No-AI 复盘")
    assert controller.sendCoachTurnConfigured(
        "请告诉我下一步该核对什么。", "coach", "", "none", False, True
    )
    assert controller.coachStreaming is False
    assert [item["role"] for item in controller.coachMessages[-2:]] == [
        "user",
        "assistant",
    ]
    assert "未调用任何模型" in controller.coachMessages[-1]["content"]
    assert controller.submissionText == before_submission
    assert profile_paths(root, "coach-user").events_file.read_text(encoding="utf-8") == before_events
    controller.shutdown()

    reopened = AppController(root, profile_id="coach-user")
    assert reopened.coachSessions
    assert reopened.coachMessages[-1]["role"] == "assistant"
    assert reopened.coachMessages[-1]["metadata"]["provider_kind"] == "none"
    reopened.shutdown()


def test_late_coach_delta_and_completion_after_stop_are_ignored(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="race-user")
    assert controller.completeOnboarding(
        "race-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    assert controller.createCoachSession("coach", "none", "", "Race")
    session = controller._coach_session()
    assert session is not None
    assistant = coach_message("assistant", "partial")
    session["messages"].append(assistant)
    operation_id = "race-operation"
    identity = ("race-user", session["session_id"], operation_id, assistant["message_id"], "provider")
    session["status"] = "streaming"
    session["last_turn"] = {
        "profile_id": "race-user",
        "session_id": session["session_id"],
        "operation_id": operation_id,
        "message_id": assistant["message_id"],
        "provider_kind": "provider",
        "provider_id": "provider",
        "model": "model",
        "mode": "coach",
        "include_submission": False,
        "include_test_output": True,
    }
    controller._coach_identity = identity
    controller._coach_cancel_event = threading.Event()
    controller._set_coach_streaming(True)
    assert controller.stopCoachTurn() is True
    stopped_content = assistant["content"]
    controller._coach_emit_delta(identity, " late chunk")
    controller._coach_turn_finished(identity, {"cancelled": False})
    assert assistant["content"] == stopped_content
    assert session["status"] == "stopped"
    assert controller.coachStreaming is False
    controller.shutdown()


def test_controller_recovers_streaming_marker_as_stopped(tmp_path: Path, qapp) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    _profile(root, "recover-user")
    session = new_coach_session(root, "recover-user")
    session["status"] = "streaming"
    write_coach_sessions(root, "recover-user", [session])

    controller = AppController(root, profile_id="recover-user")
    assert controller.coachSessions[0]["status"] == "stopped"
    persisted = json.loads(coach_sessions_path(root, "recover-user").read_text(encoding="utf-8"))
    assert persisted["sessions"][0]["status"] == "stopped"
    controller.shutdown()
