"""Small regression contracts for the Alpha.3 first-use hotfixes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.application import ApplicationService
from llm_interview_lab import __version__
from llm_interview_lab.desktop import runtime
from llm_interview_lab.desktop.controller import AppController
from llm_interview_lab.grader import GraderResult
from llm_interview_lab.workspace import (
    init_profile,
    profile_id_for_display_name,
    profile_id_from_display_name,
    profile_paths,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_display_name_is_separate_from_safe_profile_id_and_legacy_ids_resume(
    tmp_path: Path,
) -> None:
    root = _repository(tmp_path)
    assert profile_id_from_display_name("洪洲的后训练秋招准备").startswith("profile-")

    init_profile(root, "legacy-user")
    profile = profile_paths(root, "legacy-user").profile_file
    import yaml

    data = yaml.safe_load(profile.read_text(encoding="utf-8"))
    data.pop("display_name", None)
    profile.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert profile_id_for_display_name(root, "legacy-user") == "legacy-user"

    init_profile(root, "my-profile", display_name="已有档案")
    assert profile_id_for_display_name(root, "My Profile") == "my-profile-2"


def test_chinese_display_name_onboarding_persists_and_reopens(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="default")
    assert controller.completeOnboardingWithDisplayName(
        "洪洲的后训练秋招准备",
        "post_training_engineer",
        "new_grad",
        "disabled",
        "{}",
    )
    profile_id = controller.profileId
    assert profile_id.startswith("profile-")
    assert controller.profileDisplayName == "洪洲的后训练秋招准备"
    controller.shutdown()

    reopened = AppController(root, profile_id=profile_id)
    assert not reopened.onboardingRequired
    assert reopened.profileDisplayName == "洪洲的后训练秋招准备"
    reopened.shutdown()


def test_symlink_candidate_is_never_reused(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    profiles = root / "workspace/profiles"
    target = tmp_path / "outside"
    target.mkdir()
    link = profiles / "linked-profile"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    # The helper may allocate a suffix, but it must not read or write through
    # the linked directory.
    assert profile_id_for_display_name(root, "linked profile") != "linked-profile"
    assert not (target / "profile.yaml").exists()


def test_editor_snapshot_is_saved_before_grading_and_records_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile("alpha-user")
    service.start_practice("alpha-user", "FND-001")
    source = "def count_wrong_predictions(label, predictions):\n    return 0\n"
    expected_sha = hashlib.sha256(source.encode()).hexdigest()

    def fake_grader(**kwargs):
        assert kwargs["submission_path"].read_text(encoding="utf-8") == source
        return GraderResult(expected_sha, 0, "passed", 1, 0, 2, "1 passed")

    monkeypatch.setattr("llm_interview_lab.application.run_public_tests", fake_grader)
    result = service.run_practice_tests_for_submission(
        "alpha-user", "FND-001", source, operation_id="op-alpha3"
    )
    assert result.status == "passed"
    events = [
        json.loads(line)
        for line in profile_paths(root, "alpha-user").events_file.read_text(encoding="utf-8").splitlines()
    ]
    test_event = [event for event in events if event["event_type"] == "public_tests_run"][-1]
    assert test_event["payload"]["operation_id"] == "op-alpha3"
    assert test_event["payload"]["submission_sha256"] == expected_sha


def test_controller_rejects_duplicate_test_while_busy(qapp=None) -> None:
    del qapp
    controller = AppController(REPO_ROOT, demo_page="exercise")
    messages: list[str] = []
    controller.toast.connect(messages.append)
    controller._busy = True
    controller.runTestsForCurrentSubmission("def stale(): pass\n")
    assert messages == ["测试正在进行，请稍候。"]
    controller.shutdown()


def test_codex_availability_property_is_cached_not_a_path_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = AppController(REPO_ROOT, demo_page="home")

    def fail_if_called(*args, **kwargs):
        del args, kwargs
        raise AssertionError("property getter must not scan PATH")

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.discover_codex_executable",
        fail_if_called,
    )
    assert controller.codexAvailable is False
    controller.shutdown()


def test_problem_cards_distinguish_recommendation_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    service = ApplicationService(root)
    service.initialize_profile(
        "alpha-user", role_id="post_training_engineer", ai_mode="disabled"
    )
    monkeypatch.setattr(
        "llm_interview_lab.application.importlib.util.find_spec", lambda _: None
    )
    cards = {card["problem_id"]: card for card in service.problem_cards("alpha-user")}
    assert cards["FND-001"]["environment_available"] is True
    assert cards["FND-001"]["recommended_rank"] == -1
    assert cards["LOSS-014"]["recommended_rank"] >= 0
    assert cards["LOSS-014"]["environment_available"] is False
    assert cards["LOSS-014"]["environment"] == "需要 PyTorch 练习环境"


def test_active_interview_is_restored_for_the_same_profile(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    first = AppController(root, profile_id="resume-user")
    assert first.completeOnboarding(
        "resume-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    first.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "disabled"
    )
    interview_id = first.interview["interview_id"]
    first.shutdown()

    reopened = AppController(root, profile_id="resume-user")
    assert reopened.interview["interview_id"] == interview_id
    assert reopened.interview["status"] == "active"
    assert reopened.interview["resume_available"] is True
    reopened.resumeInterview()
    assert reopened.currentPage == "interview"
    reopened.shutdown()


def test_bootstrap_event_contains_runtime_fields_without_absolute_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "logs" / "bootstrap.log"
    monkeypatch.setenv("LLM_LAB_BOOTSTRAP_LOG", str(log))
    path = runtime.record_bootstrap_event(
        "controller", error=RuntimeError(f"failed at {tmp_path / 'private'}")
    )
    event = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    for key in (
        "app_version",
        "build_commit",
        "executable_path",
        "app_data_path",
        "platform",
        "python_runtime",
        "startup_stage",
        "exception_type",
        "sanitized_exception",
    ):
        assert key in event
    assert str(tmp_path) not in json.dumps(event, ensure_ascii=False)
    assert "<local-path>" in event["sanitized_exception"]


def test_bootstrap_sanitizer_redacts_unknown_paths_with_spaces() -> None:
    error = RuntimeError(
        r"failed at C:\Users\Example User\Desktop\profile data\submission.py"
    )
    sanitized = runtime._sanitized_bootstrap_message(error)
    assert "<local-path>" in sanitized
    assert "Example User" not in sanitized
    assert "profile data" not in sanitized


def test_desktop_entry_accepts_explicit_window_size_and_role_step() -> None:
    source = (REPO_ROOT / "src/llm_interview_lab/desktop/main.py").read_text(
        encoding="utf-8"
    )
    assert "--window-size" in source
    assert "--onboarding-step" in source
    assert "--onboarding-role" in source
    assert "window.resize(*args.window_size)" in source
    assert 'onboarding.setProperty("selectedRole", args.onboarding_role)' in source


def test_screenshot_manifest_is_current_synthetic_chinese_evidence() -> None:
    manifest = json.loads(
        (REPO_ROOT / "docs/images/screenshot-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == __version__
    assert manifest["language"] == "zh-CN"
    assert manifest["synthetic"] is True
    assert len(manifest["source_commit"]) == 40
    paths = {entry["path"] for entry in manifest["screenshots"]}
    expected = {
        "docs/images/desktop-onboarding.png",
        "docs/images/desktop-home.png",
        "docs/images/desktop-learn.png",
        "docs/images/desktop-exercise.png",
        "docs/images/desktop-interview.png",
        "docs/images/desktop-connections.png",
        "docs/images/onboarding-hotfix-1080x680.png",
        "docs/images/onboarding-hotfix-1280x800.png",
        "docs/images/onboarding-hotfix-1440x900.png",
    }
    assert paths == expected
    for entry in manifest["screenshots"]:
        path = REPO_ROOT / entry["path"]
        assert path.is_file()
        assert entry["source_commit"] == manifest["source_commit"]
        assert entry["synthetic"] is True
        assert entry["theme"] == "light"
        assert entry["font_scale"] == 1.0
        assert len(entry["sha256"]) == 64
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_practice_and_interview_surfaces_do_not_expose_fake_actions() -> None:
    exercise = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/ExercisePage.qml"
    ).read_text(encoding="utf-8")
    interview = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml"
    ).read_text(encoding="utf-8")
    assert "在 AI 教练中打开当前任务" in exercise
    assert "发送消息" not in exercise
    assert "value: 3" not in interview
    assert "提交并锁定回答" in interview
    assert "refreshInterviewClock" in interview
    assert "候选人自评 Rubric" in interview
