from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtTest import QTest

from llm_interview_lab.desktop.controller import (
    AppController,
    _codex_terminal_outcome,
    _decode_ai_assessment,
)
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


def _wait_for(predicate, *, attempts: int = 20, interval_ms: int = 50) -> bool:
    for _ in range(attempts):
        if predicate():
            return True
        QTest.qWait(interval_ms)
    return predicate()


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
    assert _wait_for(lambda: len(controller.materials) == 1)
    assert controller.materials[0]["ai_access"] is True

    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "disabled"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
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


def test_controller_rehydrates_question_scoped_coding_grader_revision(
    tmp_path: Path, qapp
) -> None:
    """A persisted coding result remains usable after the desktop reloads."""

    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="coding-user")
    controller.completeOnboarding(
        "coding-user", "applied_ai_engineer", "intern", "disabled", "{}"
    )
    controller.createConfiguredInterview(
        "applied_ai_engineer", "intern", "medium", "disabled"
    )
    assert controller.interview.get("question")
    question = controller.interview["question"]
    assert question["kind"] == "coding"
    interview_id = controller.interview["interview_id"]
    coding_path = (
        profile_paths(root, "coding-user").interviews_root
        / interview_id
        / "coding"
        / question["question_id"]
        / "submission.py"
    )
    digest = hashlib.sha256(coding_path.read_bytes()).hexdigest()
    session_path = (
        profile_paths(root, "coding-user").interviews_root
        / interview_id
        / "session.json"
    )
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["coding_evidence"][question["question_id"]] = {
        "submission_sha256": digest,
        "status": "passed",
        "passed": 2,
        "failed": 0,
        "duration_ms": 20,
        "recorded_at": "2026-08-30T08:00:00Z",
    }
    session_path.write_text(json.dumps(session), encoding="utf-8")

    controller._load_interview(interview_id)
    assert controller.interview["coding_tested_revision"] == digest
    assert controller.interview["coding_test_current"] is True
    assert controller.interview["phase"] == "assessment"
    controller.shutdown()


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"turn": {"status": "completed"}}, ("completed", "")),
        (
            {"turn": {"status": "failed", "error": {"message": "quota"}}},
            ("error", "quota"),
        ),
        (
            {"status": "interrupted"},
            ("cancelled", "Codex 回答已停止，未生成完整结果。"),
        ),
        ({"status": "future_status"}, ("error", "Codex 返回未完成状态（future_status），请重试。")),
    ],
)
def test_codex_terminal_metadata_never_masks_a_failed_turn(params, expected) -> None:
    assert _codex_terminal_outcome(params) == expected


def test_demo_controller_exposes_every_page_and_keeps_demo_settings_deterministic(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    persisted = QSettings("ComistryMo", "LLMInterviewLab")
    persisted.setValue("codexExecutable", "/private/maintainer/codex")
    persisted.setValue("theme", "dark")
    persisted.setValue("fontScale", 1.3)
    persisted.sync()
    first = AppController(REPO_ROOT, demo_page="home")
    assert first.codexExecutable == ""
    assert first.codexAvailable is False
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
    first.setCodexExecutable("/private/maintainer/codex")
    first.clearCodexExecutable()
    first.navigate("exercise")
    first.saveSubmission("def demo():\n    return 1\n")
    first.runTests()
    assert "PASS" in first.testOutput
    first.shutdown()

    persisted.sync()
    assert persisted.value("codexExecutable") == "/private/maintainer/codex"
    assert persisted.value("theme") == "dark"
    assert float(persisted.value("fontScale")) == pytest.approx(1.3)

    # Demo/screenshot controllers intentionally do not inherit persisted user
    # preferences; otherwise release evidence would vary with the maintainer's
    # local settings.  Normal controllers still restore them (covered by the
    # dedicated settings tests).
    restored = AppController(REPO_ROOT, demo_page="home")
    assert restored.theme == "light"
    assert restored.fontScale == pytest.approx(1.0)
    restored.testConnection("ollama-local")
    restored.shutdown()


def test_demo_controller_never_persists_connections_or_legacy_paths(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    legacy = tmp_path / "legacy-data"
    legacy.mkdir()
    root = _repository(tmp_path)
    controller = AppController(
        root, demo_page="settings", legacy_data_root=legacy
    )
    assert controller.legacyMigrationAvailable is False
    assert controller.legacyDataDirectory == ""
    assert controller.saveConnection(
        "demo-provider", "openai", "model", "Demo", "", "not-a-real-key"
    ) is False
    assert controller.deleteConnection("ollama-local") is False
    assert not (root / "workspace/profiles/demo/connections.json").exists()
    controller.shutdown()


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
    assert _wait_for(lambda: controller.interview.get("question") is not None)
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


def test_delayed_provider_assessment_cannot_rewrite_frozen_evidence(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="delayed-provider-user")
    controller.completeOnboarding(
        "delayed-provider-user", "ai_product_manager", "new_grad", "provider", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "provider"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
    question = controller.interview["question"]
    answer = "I define assumptions, evidence, risks, and a reversible rollout."
    controller.lockInterviewAnswer(answer)
    callbacks: dict[str, object] = {}

    def delayed_background(operation, complete, failed=None):
        del operation, failed
        callbacks["complete"] = complete

    monkeypatch.setattr(controller, "_background", delayed_background)
    controller.assessInterviewWithProvider(answer, "unused-connection", False)
    self_scores = {name: 3 for name in question["rubric"]["dimensions"]}
    controller.answerInterviewDetailed(
        answer,
        json.dumps(self_scores),
        "The answer explicitly states assumptions, evidence, risks, and rollback.",
    )
    controller.finishInterview()
    frozen = controller.service.interview_session(
        "delayed-provider-user", controller.interview["interview_id"]
    )
    callback = callbacks["complete"]
    assert callable(callback)
    callback(
        {
            "scores": {name: 5 for name in question["rubric"]["dimensions"]},
            "evidence": "Late AI evidence must not replace frozen self evidence.",
            "confidence": "high",
            "fatal_issues": [],
            "follow_up": "",
        }
    )
    restored = controller.service.interview_session(
        "delayed-provider-user", controller.interview["interview_id"]
    )
    assert restored["assessments"] == frozen["assessments"]
    assert restored["result"] == frozen["result"]
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
    assert _wait_for(lambda: controller.interview.get("question") is not None)
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
    assert _wait_for(lambda: controller.interview.get("question") is not None)
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


def test_tampered_interview_answer_path_cannot_escape_the_profile(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="path-guard-user")
    controller.completeOnboarding(
        "path-guard-user", "ai_product_manager", "new_grad", "disabled", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "disabled"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
    question = controller.interview["question"]
    controller.lockInterviewAnswer("Canonical locked answer.")
    interview_id = controller.interview["interview_id"]
    controller.shutdown()

    secret = root / "outside-secret.txt"
    secret.write_text("must never appear in the interview UI", encoding="utf-8")
    session_path = (
        profile_paths(root, "path-guard-user").interviews_root
        / interview_id
        / "session.json"
    )
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["answers"][question["question_id"]] = {
        "relative_path": "../../../outside-secret.txt",
        "sha256": hashlib.sha256(secret.read_bytes()).hexdigest(),
        "recorded_at": session["answers"][question["question_id"]]["recorded_at"],
    }
    session_path.write_text(json.dumps(session), encoding="utf-8")

    restored = AppController(root, profile_id="path-guard-user")
    assert restored.interview["answer_corrupted"] is True
    assert "must never appear" not in restored.interview["answer_text"]
    restored.shutdown()

    session["answers"][question["question_id"]]["relative_path"] = ""
    session_path.write_text(json.dumps(session), encoding="utf-8")
    empty_path = AppController(root, profile_id="path-guard-user")
    assert empty_path.interview["answer_corrupted"] is True
    assert empty_path.interview["answer_text"] == ""
    empty_path.shutdown()


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
    main_qml = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml"
    ).read_text(encoding="utf-8")
    connections_qml = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/ConnectionsPage.qml"
    ).read_text(encoding="utf-8")
    # Approval is shell-owned so it remains visible while navigating away from
    # Connections; the page must not keep a second, stale approval model.
    assert 'property var pendingCodexApproval: ({})' in main_qml
    assert 'objectName: "codexApprovalDetails"' in main_qml
    assert 'window.resolveApproval("accept")' in main_qml
    assert "pendingApproval" not in connections_qml
    assert 'objectName: "saveAndTestConnection"' in connections_qml
    assert 'text: "保存并测试"' in connections_qml
    assert "if (saved)" in connections_qml
    assert "app.testConnection(connectionId.text)" in connections_qml
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
    assert "id: continueTrainingButton" in home
    assert 'text: "继续面试"' in home

    assert 'objectName: "practicePrimaryAction"' in exercise
    assert "id: practicePrimaryButton" in exercise
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


def test_home_and_learn_prioritize_primary_actions_and_secondary_metadata() -> None:
    main = (REPO_ROOT / "src/llm_interview_lab/desktop/qml/Main.qml").read_text(
        encoding="utf-8"
    )
    home = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/HomePage.qml"
    ).read_text(encoding="utf-8")
    learn = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/LearnPage.qml"
    ).read_text(encoding="utf-8")

    # The compact sidebar must ellipsize its brand copy instead of painting it
    # over the content pane at 1080px wide.
    assert 'Layout.minimumWidth: 0' in main
    assert 'maximumLineCount: 1' in main
    assert 'elide: Text.ElideRight' in main

    assert 'objectName: "homePrimaryAction"' in home
    assert 'objectName: "homeInterviewSecondaryAction"' in home
    assert home.index('objectName: "homePrimaryAction"') < home.index(
        'objectName: "homeInterviewSecondaryAction"'
    )
    assert "Layout.preferredHeight: 198" in home
    assert "text: root.trainingTarget ? root.trainingTarget.title" in home
    assert 'StatusPill {' in home

    assert 'objectName: "learnProblemList"' in learn
    assert 'objectName: "learnOpenProblemButton"' in learn
    assert "font.pixelSize: 17" in learn
    assert "maximumLineCount: 2" in learn
    assert "text: modelData.skills && modelData.skills.length ? modelData.skills.slice(0, 3).join(\" · \") : \" \"" in learn
    assert 'text: modelData.problem_id || ""' in learn
    assert learn.index('text: modelData.title; color: root.palette.text; font.bold: true; font.pixelSize: 17') < learn.index(
        'text: modelData.problem_id || ""'
    )
    assert learn.index('text: modelData.problem_id || ""') < learn.index(
        'objectName: "learnOpenProblemButton"'
    )


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
    assert "root.roundTypeText(item.round || item.type || \"\")" in interview
    assert "no_strict_candidate" in interview
    assert 'item.skills.join("、")' not in interview
    assert "root.assessmentSourceText(modelData.source)" in interview
    assert "root.confidenceText(modelData.confidence)" in interview
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
    # The interview editor must fill the question panel viewport; otherwise
    # ScrollView sizes its content to the TextArea implicit width and the
    # phase row collides with the submit action.
    assert 'id: questionScroll' in interview
    assert 'contentWidth: availableWidth' in interview
    assert 'width: questionScroll.availableWidth' in interview
    assert 'objectName: "interviewPhasePill"' in interview
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
