from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_interview_lab.desktop import runtime
from llm_interview_lab.desktop.main import _startup_error_code, main
from llm_interview_lab.desktop.runtime import (
    bootstrap_log_path,
    record_bootstrap_event,
    show_startup_error,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_bootstrap_log_is_available_before_repository_and_sanitizes_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_app_data = tmp_path / "本地 数据"
    private_data = local_app_data / "private workspace"
    monkeypatch.setattr(runtime.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(private_data))
    monkeypatch.delenv("LLM_LAB_BOOTSTRAP_LOG", raising=False)

    path = record_bootstrap_event("process_started", runtime_assets_found=True)
    record_bootstrap_event(
        "controller",
        error=RuntimeError(f"failed below {private_data}"),
    )

    assert path == local_app_data / "LLMInterviewLab/logs/bootstrap.log"
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert events[0]["startup_stage"] == "process_started"
    assert events[0]["runtime_assets_found"] is True
    assert events[1]["exception_type"] == "RuntimeError"
    assert str(private_data) not in events[1]["message"]
    assert "<local-path>" in events[1]["message"]


def test_startup_error_has_visible_reason_code_and_log_location(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LLM_LAB_SUPPRESS_STARTUP_DIALOG", "1")
    path = tmp_path / "bootstrap.log"

    show_startup_error("QML_LOAD_FAILED", "桌面界面加载失败。", path)

    message = capsys.readouterr().err
    assert "桌面界面加载失败" in message
    assert "QML_LOAD_FAILED" in message
    assert str(path) in message


@pytest.mark.parametrize(
    ("stage", "message", "expected"),
    [
        ("runtime_assets", "missing", "RUNTIME_ASSETS_MISSING"),
        ("repository", "permission denied", "DATA_DIRECTORY_UNAVAILABLE"),
        ("controller", "bad state", "CONTROLLER_INITIALIZATION_FAILED"),
        ("qml", "root object missing", "QML_LOAD_FAILED"),
    ],
)
def test_startup_failures_use_stable_actionable_codes(
    stage: str, message: str, expected: str
) -> None:
    assert _startup_error_code(stage, RuntimeError(message)) == expected


def test_missing_packaged_assets_fail_before_qt_with_bootstrap_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "incomplete bundle"
    bundle.mkdir()
    log_path = tmp_path / "logs/bootstrap.log"
    monkeypatch.setenv("LLM_LAB_PACKAGED", "1")
    monkeypatch.setenv("LLM_LAB_BUNDLE_ROOT", str(bundle))
    monkeypatch.setenv("LLM_LAB_BOOTSTRAP_LOG", str(log_path))
    monkeypatch.setenv("LLM_LAB_SUPPRESS_STARTUP_DIALOG", "1")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    assert main(["--smoke-test"]) == 2

    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [event["startup_stage"] for event in events] == [
        "process_started",
        "runtime_assets",
    ]
    assert events[-1]["runtime_assets_found"] is False
    assert events[-1]["exception_type"] == "RuntimeError"


def test_windows_release_uses_one_standalone_portable_bundle() -> None:
    spec = (REPO_ROOT / "scripts/pysidedeploy.spec").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    checker = (REPO_ROOT / "scripts/check_desktop_artifact.py").read_text(
        encoding="utf-8"
    )

    assert "mode = standalone" in spec
    assert "mode = onefile" not in spec
    assert "Directory.Name -eq 'LLMInterviewLab.dist'" in workflow
    assert "Rename-Item -LiteralPath $generatedExecutable -NewName 'LLMInterviewLab.exe'" in workflow
    assert "dist/release/LLMInterviewLab/LLMInterviewLab.exe" in workflow
    assert "LLMInterviewLab-Windows-x64-portable.zip" in workflow
    assert "LLMInterviewLab-Windows-x64.exe" not in workflow
    assert "--bundle-root" in checker
    assert "runtime_assets/curriculum" in checker
    assert '"startup_stage": "first_window"' in checker
    assert "screenshot_bytes=" in checker
    assert "sampled_colors" in checker
    assert "image.width() >= 1100" in checker


def test_screenshot_captures_the_qt_quick_scene() -> None:
    entrypoint = (
        REPO_ROOT / "src/llm_interview_lab/desktop/main.py"
    ).read_text(encoding="utf-8")

    assert "shiboken6.wrapInstance(" in entrypoint
    assert "quick_window.grabWindow()" in entrypoint
    assert "screen.grabWindow(window.winId())" not in entrypoint
