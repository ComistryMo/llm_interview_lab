from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QSettings

from llm_interview_lab.desktop.controller import AppController, _decode_ai_assessment
from llm_interview_lab.desktop.runtime import prepare_desktop_repository
from llm_interview_lab.pytest_plugin import (
    ENV_SUBMISSION,
    ENV_SUBMISSIONS_ROOT,
    ENV_SYMBOL,
)
from llm_interview_lab.workspace import init_profile, load_profile, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def qapp():
    application = QGuiApplication.instance() or QGuiApplication(["desktop-tests"])
    yield application


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='desktop-fixture'\nversion='0'\n", encoding="utf-8"
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


def test_controller_first_launch_role_material_practice_and_interview(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="desktop-user")
    assert controller.onboardingRequired
    controller.completeOnboarding(
        "desktop-user",
        "ai_product_manager",
        "new_grad",
        "disabled",
        "{}",
    )
    assert not controller.onboardingRequired
    assert controller.dashboard["role"]["primary_role"] == "ai_product_manager"
    assert controller.currentPage in {"home", "exercise"}
    profile = load_profile(profile_paths(root, "desktop-user"), root)
    assert profile["role_preferences"]["ai_mode"] == "disabled"

    source = tmp_path / "career-intent.md"
    source.write_text("Synthetic intent: applied AI roles.\n", encoding="utf-8")
    controller.addMaterial(str(source), "career_intent", "Synthetic intent", True)
    assert len(controller.materials) == 1
    assert controller.materials[0]["ai_access"] is True

    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "disabled"
    )
    assert controller.interview["status"] == "active"
    question = controller.interview["question"]
    assert question["kind"] != "coding"
    controller.answerInterview(
        "I state assumptions, define a measurable outcome, and compare failure modes.",
        3,
        "The answer explicitly states assumptions, outcomes, and failure modes.",
    )
    controller.finishInterview()
    assert controller.interview["status"] == "incomplete"
    assert controller.interview["result"]["completion_status"] == "incomplete"
    assert controller.interview["result"]["assessment_evidence"][0]["source"] == "self"
    status = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--untracked-files=all",
            "--",
            "workspace/profiles/desktop-user",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert status.stdout == ""
    controller.shutdown()


def test_demo_controller_exposes_every_page_and_restores_settings(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    first = AppController(REPO_ROOT, demo_page="home")
    for page in (
        "home",
        "career",
        "learn",
        "exercise",
        "interview",
        "coach",
        "progress",
        "connections",
        "settings",
    ):
        first.navigate(page)
        assert first.currentPage == page
    first.setTheme("dark")
    first.setFontScale(1.25)
    first.navigate("exercise")
    first.saveSubmission("def demo():\n    return 1\n")
    first.runTests()
    assert "PASS" in first.testOutput
    first.shutdown()

    restored = AppController(REPO_ROOT, demo_page="home")
    assert restored.theme == "dark"
    assert restored.fontScale == pytest.approx(1.25)
    restored.testConnection("ollama-local")
    restored.shutdown()


def test_qml_offscreen_smoke_and_version_do_not_need_a_profile(tmp_path: Path) -> None:
    screenshot = tmp_path / "connections.png"
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "llm_interview_lab.desktop.main",
            "--screenshot",
            str(screenshot),
            "--screenshot-page",
            "connections",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Unable to assign" not in completed.stderr
    version = subprocess.run(
        [sys.executable, "-m", "llm_interview_lab.desktop.main", "--version"],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert version.returncode == 0
    assert version.stdout.startswith("llm-lab-gui ")


def test_desktop_executable_entry_can_host_the_isolated_grader_worker() -> None:
    fixture = REPO_ROOT / "tests/fixtures/grader/add_one"
    environment = {
        **os.environ,
        ENV_SUBMISSION: str(fixture / "submissions/valid.py"),
        ENV_SUBMISSIONS_ROOT: str(fixture / "submissions"),
        ENV_SYMBOL: "add_one",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "llm_interview_lab.desktop.main",
            "--grader-worker",
            str(fixture / "test_public.py"),
            "-q",
            "--capture=no",
            "-p",
            "llm_interview_lab.pytest_plugin",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "2 passed" in completed.stdout


def test_ai_interview_scorecard_requires_exact_rubric_and_evidence() -> None:
    parsed = _decode_ai_assessment(
        '{"scores":{"tradeoffs":4},"evidence":"The candidate compared latency and quality explicitly.",'
        '"confidence":"medium","fatal_issues":[],"follow_up":"How would you measure it?"}',
        {"tradeoffs"},
        {"invents_user_data"},
    )
    assert parsed["scores"] == {"tradeoffs": 4}
    assert parsed["follow_up"].startswith("How")
    with pytest.raises(RuntimeError, match="dimensions"):
        _decode_ai_assessment(
            '{"scores":{"eloquence":5},"evidence":"This is long enough evidence for the parser.",'
            '"confidence":"high","fatal_issues":[],"follow_up":""}',
            {"tradeoffs"},
            set(),
        )


def test_provider_assessment_scores_the_locked_answer_once(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="provider-user")
    controller.completeOnboarding(
        "provider-user", "ai_product_manager", "new_grad", "provider", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "provider"
    )
    question = controller.interview["question"]
    answer = "I state assumptions, success metrics, trade-offs, and rollback evidence."
    controller.lockInterviewAnswer(answer)
    scores = {name: 4 for name in question["rubric"]["dimensions"]}

    def synchronous_background(operation, complete, failed=None):
        del operation, failed
        complete(
            {
                "scores": scores,
                "evidence": "The locked answer names assumptions, metrics, trade-offs, and rollback.",
                "confidence": "high",
                "fatal_issues": [],
                "follow_up": "",
            }
        )

    monkeypatch.setattr(controller, "_background", synchronous_background)
    controller.assessInterviewWithProvider(answer, "unused-connection", False)

    session = controller.service.interview_session(
        "provider-user", controller.interview["interview_id"]
    )
    assert list(session["answers"]) == [question["question_id"]]
    assert session["assessments"][question["question_id"]]["source"] == "ai"
    controller.shutdown()


def test_controller_loads_and_saves_a_timed_coding_round(tmp_path: Path, qapp) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="coding-user")
    controller.completeOnboarding(
        "coding-user", "applied_ai_engineer", "new_grad", "disabled", "{}"
    )
    controller.createConfiguredInterview(
        "applied_ai_engineer", "new_grad", "medium", "disabled"
    )
    assert controller.interview["question"]["kind"] == "coding"
    original = controller.interview["coding_text"]
    controller.saveInterviewCoding(original + "\n# timed local change\n")
    stored = controller.service.current_interview_coding_submission(
        "coding-user", controller.interview["interview_id"]
    )
    assert stored["text"].endswith("# timed local change\n")
    controller.shutdown()


def test_locked_interview_answer_corruption_is_visible_and_blocks_scoring(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="corrupt-answer-user")
    controller.completeOnboarding(
        "corrupt-answer-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "disabled"
    )
    question = controller.interview["question"]
    controller.lockInterviewAnswer(
        "I define assumptions, measurable evidence, and a reversible rollout."
    )
    session = controller.service.interview_session(
        "corrupt-answer-user", controller.interview["interview_id"]
    )
    record = session["answers"][question["question_id"]]
    profile_paths(root, "corrupt-answer-user").root.joinpath(
        *record["relative_path"].split("/")
    ).unlink()
    controller.shutdown()

    restored = AppController(root, profile_id="corrupt-answer-user")
    assert restored.interview["answer_locked"] is True
    assert restored.interview["answer_corrupted"] is True
    assert "校验失败" in restored.interview["answer_error"]
    restored.shutdown()


def test_standalone_runtime_seeds_public_assets_without_touching_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "local-app-data"
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(outside)
    monkeypatch.setenv("LLM_LAB_BUNDLE_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("LLM_LAB_DESKTOP_DATA_ROOT", str(data_root))

    root = prepare_desktop_repository()
    assert root == data_root
    assert (root / ".llm-lab-standalone.json").is_file()
    assert (root / "curriculum/catalog").is_dir()
    created = init_profile(root, "standalone-user")
    sentinel = created.paths.root / "materials/keep-me.txt"
    sentinel.write_text("private local evidence\n", encoding="utf-8")

    marker = root / ".llm-lab-standalone.json"
    marker.write_text(
        '{"schema_version":1,"version":"older","synthetic":true}\n',
        encoding="utf-8",
    )
    assert prepare_desktop_repository() == root
    assert sentinel.read_text(encoding="utf-8") == "private local evidence\n"


def test_desktop_release_configuration_is_portable_and_separate_from_core_ci() -> None:
    spec = (REPO_ROOT / "scripts/pysidedeploy.spec").read_text(encoding="utf-8")
    mac_spec = (REPO_ROOT / "scripts/pysidedeploy-macos.spec").read_text(
        encoding="utf-8"
    )
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "E:\\" not in spec
    assert "python_path = \n" in spec
    assert "desktop-windows:" in workflow
    assert 'python -m pip install -e ".[desktop,ai,dev]"' in workflow
    repository_job, desktop_job = workflow.split("  desktop-windows:", maxsplit=1)
    assert ".[desktop" not in repository_job
    assert "torch" not in desktop_job.lower()
    assert "check_desktop_artifact.py" in desktop_job
    assert "LLMInterviewLab-Windows-x64-portable.zip" in desktop_job
    assert "New-Item -ItemType Directory -Force -Path dist/desktop" in desktop_job
    assert "mode = standalone" in spec
    assert "mode = onefile" not in spec
    assert "--bundle-root dist/release/LLMInterviewLab" in desktop_job
    assert "LLMInterviewLab-Windows-x64.exe" not in desktop_job
    assert "curriculum/problems/=**/*.py" in spec
    assert "curriculum/retention/=**/*.py" in spec
    assert "--include-package=httpx" in spec
    assert "--nofollow-import-to=any_llm" in spec
    checker = (REPO_ROOT / "scripts/check_desktop_artifact.py").read_text(
        encoding="utf-8"
    )
    assert '"LLM_LAB_DESKTOP_DATA_ROOT"' in checker
    connections_qml = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/ConnectionsPage.qml"
    ).read_text(encoding="utf-8")
    assert "pendingApproval.diff" in connections_qml
    assert "仅批准本次" in connections_qml
    assert "desktop-macos-arm64:" in workflow
    assert "runs-on: macos-15" in workflow
    assert "LLMInterviewLab-macOS-arm64.app.zip" in workflow
    assert "LLMInterviewLab-macOS-arm64.dmg" in workflow
    # pyside6-deploy derives both options from the macOS icon field.  Repeating
    # them in ``extra_args`` makes Nuitka reject the build as two icon files.
    assert "icon = dist/icons/LLMInterviewLab.icns" in mac_spec
    assert "--macos-app-icon" not in mac_spec
    assert "--macos-create-app-bundle" not in mac_spec


def test_home_and_practice_expose_truthful_next_actions() -> None:
    home = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/HomePage.qml"
    ).read_text(encoding="utf-8")
    exercise = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/ExercisePage.qml"
    ).read_text(encoding="utf-8")

    assert 'in_progress: "答案仍在编辑；下一步运行公开测试并修复失败。"' in home
    assert "app.startRetentionFor(modelData.problem_id, modelData.stage)" in home
    assert 'objectName: "dueRetentionList"' in home
    assert "modelData.blocked_reason" in home

    assert 'objectName: "practicePrimaryAction"' in exercise
    assert "root.actions.review || ({})" in exercise
    assert "root.actions.retention || ({})" in exercise
    assert 'if (review.state === "complete")' in exercise
    assert 'review.state && review.state !== "complete"' not in exercise
    assert 'item.state !== "complete"' in exercise
    assert 'retention.state === "due" || retention.state === "in_progress"' in exercise
    assert 'return "review"' in exercise
    assert 'return "retention"' in exercise
    assert "app.runTestsForCurrentSubmission(editor.text)" in exercise
    assert "app.startRetentionFor(app.currentTask.problem_id, root.nextRetentionAction().stage)" in exercise
    assert "root.retentionBlockedText(retention)" in exercise
    assert "root.actions.retention_stage" not in exercise
    assert "root.actions.retention_due" not in exercise
    assert 'app.navigate("coach")' in exercise
    assert "startRetentionStage(\"d2\")" not in exercise
    assert "startRetentionStage(\"d7\")" not in exercise
    assert 'id: helpLevel' not in exercise
    assert 'font.family: "Cascadia Mono, Consolas, monospace"' not in exercise


def test_interview_setup_uses_profile_role_availability_and_real_report() -> None:
    interview = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml"
    ).read_text(encoding="utf-8")

    assert "app.dashboard.role.primary_role" in interview
    assert "app.interviewConfiguration(roleId, seniority.currentValue, difficulty.currentValue)" in interview
    assert 'objectName: "interviewConfigurationMessage"' in interview
    assert "root.configuration.available !== false" in interview
    assert "root.configuration.missing_rounds" in interview
    assert "root.configuration.missing_environment" in interview
    assert "root.missingRoundLabel(rounds[i])" in interview
    assert 'item.round || item.type || "未命名环节"' in interview
    assert 'item.skills.join("、")' in interview
    assert 'rounds.join("、")' not in interview
    assert 'role.currentValue || "applied_ai_engineer"' not in interview

    assert 'objectName: "interviewResultCard"' in interview
    for evidence_field in (
        "result.overall_score",
        "root.interviewResult.completion_status",
        "root.interviewResult.assessment_evidence",
        "modelData.source",
        "modelData.evidence",
        "modelData.confidence",
        "root.interviewResult.critical_gaps",
        "result.unscored",
    ):
        assert evidence_field in interview
    assert "root.interviewResult.source" not in interview
    assert "root.interviewResult.evidence" not in interview
    assert "root.interviewResult.confidence" not in interview
    assert "不会改变刷题训练的掌握状态" in interview
    assert 'font.family: "Cascadia Mono, Consolas, monospace"' not in interview


@pytest.mark.parametrize("page", ["home", "exercise", "interview"])
def test_truthful_desktop_pages_render_at_1080x680(
    page: str, tmp_path: Path
) -> None:
    screenshot = tmp_path / f"{page}.png"
    environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "llm_interview_lab.desktop.main",
            "--screenshot",
            str(screenshot),
            "--screenshot-page",
            page,
            "--window-size",
            "1080x680",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert screenshot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "TypeError" not in completed.stderr
    assert "ReferenceError" not in completed.stderr
    assert "Unable to assign" not in completed.stderr
