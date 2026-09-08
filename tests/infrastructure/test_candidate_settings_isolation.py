"""Explicit package/UAT settings never fall through to a real OS account."""
from tests.infrastructure.test_interview_input_runtime import qapp, public_repo

from PySide6.QtCore import QSettings

from llm_interview_lab.desktop.controller import AppController


def test_explicit_settings_file_persists_without_native_registry(qapp, public_repo, tmp_path, monkeypatch):
    path = tmp_path / "设置 UAT.ini"
    monkeypatch.setenv("LLM_LAB_DESKTOP_SETTINGS_FILE", str(path))
    monkeypatch.setattr(AppController, "refreshCodexAvailability", lambda self: None)
    constructor = QSettings
    calls = []

    def isolated_settings(*args):
        calls.append(args)
        assert args == (str(path), QSettings.IniFormat)
        return constructor(*args)

    monkeypatch.setattr("llm_interview_lab.desktop.controller.QSettings", isolated_settings)
    isolated_settings.IniFormat = QSettings.IniFormat
    first = AppController(public_repo, profile_id="synthetic-settings-candidate")
    try:
        assert first.onboardingRequired
        first.setTheme("dark")
        first.setSidebarCollapsed(True)
    finally:
        first.shutdown()
    reopened = AppController(public_repo, profile_id="synthetic-settings-candidate")
    try:
        assert reopened.onboardingRequired  # No silent Profile creation.
        assert reopened.theme == "dark"
        assert reopened.sidebarMode == "collapsed"
        assert len(calls) == 2 and path.is_file()
    finally:
        reopened.shutdown()
