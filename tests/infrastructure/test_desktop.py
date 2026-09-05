from __future__ import annotations

import hashlib
import importlib.util
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
from llm_interview_lab.ai.codex_backend import CodexEvent
from llm_interview_lab.ai.base import ChatEvent
from llm_interview_lab.ai.providers import ProviderConfig
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


def test_controller_starts_only_explicit_non_coding_interview_fallback(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="fallback-user")
    assert controller.completeOnboarding(
        "fallback-user",
        "ai_algorithm_research_engineer",
        "new_grad",
        "disabled",
        "{}",
    )
    original_find_spec = importlib.util.find_spec
    monkeypatch.setattr(
        "llm_interview_lab.role_interviews.importlib.util.find_spec",
        lambda name: None if name == "torch" else original_find_spec(name),
    )

    controller.createNonCodingInterview(
        "ai_algorithm_research_engineer",
        "new_grad",
        "medium",
        "disabled",
        "",
        False,
    )

    interview_id = controller.interview["interview_id"]
    session = controller.service.interview_session("fallback-user", interview_id)
    assert session["status"] == "active"
    assert session["delivery_mode"] == "non_coding_fallback"
    assert session["blueprint_coverage"]["full_blueprint"] is False
    assert all(question["kind"] != "coding" for question in session["questions"])
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


def test_controller_previews_context_then_confirms_real_personalized_plan(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="personalized-user")
    assert controller.completeOnboarding(
        "personalized-user",
        "post_training_engineer",
        "new_grad",
        "provider",
        "{}",
    )
    source = tmp_path / "resume.md"
    source.write_text(
        "Sanitized preference-data project. Scope and metrics require candidate confirmation.",
        encoding="utf-8",
    )
    assert controller.addMaterial(str(source), "resume", "脱敏简历", True)
    material_id = controller.materials[0]["id"]
    connection = ProviderConfig(
        "provider-main",
        "openai-compatible",
        "local-test-model",
        "测试连接",
        "http://127.0.0.1:9999/v1",
        None,
    )

    class FakeProvider:
        async def stream_chat(self, messages):
            assert "Mode=INTERVIEW_PLAN" in messages[0]["content"]
            yield ChatEvent(
                "text_delta",
                json.dumps(
                    {
                        "questions": [
                            {
                                "round_index": 1,
                                "kind": "oral",
                                "title": "偏好优化证据",
                                "prompt": "请基于已确认材料解释偏好优化的 reference policy；材料未说明的指标请先向候选人确认。",
                            },
                            {
                                "round_index": 2,
                                "kind": "evaluation_case",
                                "title": "数据验证评测",
                                "prompt": "请为材料中的偏好数据项目设计离线评测，并区分事实、推断、遗漏和失败回退。",
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
            )
            yield ChatEvent("completed")

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.list_connections",
        lambda repo_root, profile_id: (connection,),
    )
    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.create_chat_provider",
        lambda config, api_key: FakeProvider(),
    )

    def synchronous_background(operation, complete, failed=None):
        try:
            complete(operation())
        except Exception as error:
            if failed:
                failed(str(error))
            else:
                raise

    monkeypatch.setattr(controller, "_background", synchronous_background)
    context = controller.personalizedInterviewPlanContext(
        "post_training_engineer",
        "new_grad",
        "medium",
        material_id,
        True,
    )
    assert context["context_sha256"]
    assert any(part["sensitive"] for part in context["parts"])
    controller.generatePersonalizedInterviewPlan(
        "post_training_engineer",
        "new_grad",
        "medium",
        connection.connection_id,
        material_id,
        True,
        context["context_sha256"],
    )
    assert controller.interviewPlanPreview["status"] == "ready"
    assert [
        question["source"]["kind"]
        for question in controller.interviewPlanPreview["questions"]
    ] == ["catalog_problem", "ai_generated", "ai_generated"]
    assert controller.confirmPersonalizedInterviewPlan()
    assert controller.interview["status"] == "active"
    assert controller.interview["question"]["source"]["kind"] == "catalog_problem"
    session = controller.service.interview_session(
        "personalized-user", controller.interview["interview_id"]
    )
    assert session["plan_mode"] == "ai_generated"
    assert session["material_refs"][0]["id"] == material_id
    controller.shutdown()


def test_codex_personalized_plan_route_keeps_codex_mode_and_schema() -> None:
    controller = (REPO_ROOT / "src/llm_interview_lab/desktop/controller.py").read_text(
        encoding="utf-8"
    )
    application = (REPO_ROOT / "src/llm_interview_lab/application.py").read_text(
        encoding="utf-8"
    )
    assert "def generatePersonalizedInterviewPlanWithCodex" in controller
    assert "@Slot(str, str, str, str, bool, str)" in controller
    method_start = controller.index("def generatePersonalizedInterviewPlanWithCodex")
    decorator_window = controller[max(0, method_start - 100):method_start]
    assert "@Slot(str, str, str, str, str, bool, str)" not in decorator_window
    assert 'output_schema: dict[str, Any]' in controller
    assert '"provider_kind": "codex"' in controller
    assert '"ai_mode": "codex"' in controller
    assert 'ai_mode=request.get("ai_mode", "provider")' in controller
    assert 'ai_mode: str = "provider"' in application


def test_codex_dynamic_first_question_error_is_actionable_and_releases_busy(
    tmp_path: Path, qapp
) -> None:
    """App Server retry/error events must not leave the first-question UI stuck."""

    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="dynamic-codex-user")
    assert controller.completeOnboarding(
        "dynamic-codex-user", "post_training_engineer", "intern", "codex", "{}"
    )

    operation_id = "dynamic-first-question-op"
    controller._codex_backend = None
    controller._codex_thread_id = "thread-1"
    controller._codex_dynamic_initial_pending = True
    controller._codex_interview_identity = (
        "dynamic-codex-user",
        "__dynamic_initial__",
        "",
        operation_id,
        "codex",
    )
    controller._codex_interview_turn_id = "turn-1"
    controller._codex_start_ready = True
    controller._codex_start_response_turn_id = "turn-1"
    controller._interview_plan_request = {"operation_id": operation_id}
    controller._background_operations.add(operation_id)
    controller._set_busy(True)

    controller._handle_codex_event(
        CodexEvent(
            "error",
            {
                "turnId": "turn-1",
                "error": {"message": "Reconnecting... 5/5; sampling request timed out"},
                "willRetry": True,
            },
        )
    )
    assert controller.busy is True
    assert controller.interviewPlanPreview["status"] == "generating"
    assert "重试" in controller.interviewPlanPreview["user_message"]

    controller._handle_codex_event(
        CodexEvent(
            "error",
            {
                "turnId": "turn-1",
                "error": {"message": "sampling request timed out"},
                "willRetry": False,
            },
        )
    )
    assert controller.busy is False
    assert controller.interviewPlanPreview["status"] == "error"
    assert "操作未完成" not in controller.interviewPlanPreview["user_message"]
    assert "重试" in controller.interviewPlanPreview["user_message"]
    controller.shutdown()


def test_codex_dynamic_first_question_accepts_completed_item_payload(
    tmp_path: Path, qapp
) -> None:
    """Decode the authoritative completed App Server item when no deltas arrive."""

    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="dynamic-completed-user")
    assert controller.completeOnboarding(
        "dynamic-completed-user", "post_training_engineer", "intern", "codex", "{}"
    )

    controller._codex_thread_id = "thread-dynamic"
    controller._codex_thread_mode = "interviewer"
    context = controller.dynamicInterviewContextPreview(
        "post_training_engineer", "intern", "medium", "", False
    )
    allowed_kind = next(
        round_value.type
        for round_value in controller.service.roles.blueprint_for(
            "post_training_engineer", "intern"
        ).rounds
        if round_value.type != "coding"
    )
    operation_id = "dynamic-completed-op"
    controller._codex_dynamic_initial_pending = True
    controller._codex_interview_identity = (
        "dynamic-completed-user",
        "__dynamic_initial__",
        "",
        operation_id,
        "codex",
    )
    controller._codex_interview_turn_id = "turn-dynamic"
    controller._codex_interview_operation_id = operation_id
    controller._codex_start_ready = True
    controller._codex_start_response_turn_id = "turn-dynamic"
    controller._interview_plan_request = {
        "profile_id": "dynamic-completed-user",
        "operation_id": operation_id,
        "role_id": "post_training_engineer",
        "seniority": "intern",
        "difficulty": "medium",
        "material_id": "",
        "consent": False,
        "context_sha256": context["context_sha256"],
        "ai_mode": "codex",
        "allowed_kinds": [allowed_kind],
    }
    controller._background_operations.add(operation_id)
    controller._set_busy(True)
    question = {
        "kind": controller._interview_plan_request["allowed_kinds"][0],
        "title": "自我介绍与岗位目标",
        "prompt": "请用两分钟介绍你的经历，并说明你为何选择这个岗位。",
    }
    payload = {
        "turnId": "turn-dynamic",
        "item": {
            "id": "item-answer",
            "type": "agentMessage",
            "phase": "final_answer",
            "text": json.dumps(question, ensure_ascii=False),
        },
    }
    controller._handle_codex_event(CodexEvent("item/completed", payload))
    controller._handle_codex_event(
        CodexEvent(
            "turn/completed",
            {
                "threadId": "thread-dynamic",
                "turn": {
                    "id": "turn-dynamic",
                    "status": "completed",
                    "items": [payload["item"]],
                },
            },
        )
    )
    assert controller.interview["status"] == "active"
    assert controller.interview["question"]["title"] == question["title"]
    assert controller.busy is False
    controller.shutdown()


def test_dynamic_interview_enters_with_local_opening_without_waiting_for_codex(
    tmp_path: Path, qapp
) -> None:
    """The first usable screen is local; Codex is reserved for later turns."""

    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="dynamic-local-opening-user")
    assert controller.completeOnboarding(
        "dynamic-local-opening-user", "post_training_engineer", "intern", "codex", "{}"
    )

    # No Codex transport is installed in this fixture.  A local opening must
    # still create the real persisted session and enter the interview room.
    context = controller.dynamicInterviewContextPreview(
        "post_training_engineer", "intern", "hard", "", False
    )
    controller.startDynamicPersonalizedInterview(
        "post_training_engineer",
        "intern",
        "hard",
        "codex",
        "",
        False,
        context["context_sha256"],
    )
    assert controller.interview["status"] == "active"
    assert controller.interview["delivery_mode"] == "dynamic_ai"
    assert controller.interview["question"]["title"] == "自我介绍与经历概述"
    assert controller.interview["question"]["source"]["kind"] == "process_opening"
    assert controller.busy is False
    assert controller._codex_dynamic_initial_pending is False
    session_id = controller.interview["interview_id"]
    assert controller.service.interview_session(
        "dynamic-local-opening-user", session_id
    )["questions"][0]["source"]["kind"] == "process_opening"
    controller.shutdown()


def test_codex_personalized_plan_stream_is_decoded_and_persisted(
    tmp_path: Path, qapp
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="codex-plan-user")
    assert controller.completeOnboarding(
        "codex-plan-user", "post_training_engineer", "new_grad", "codex", "{}"
    )

    class FakeBackend:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def start_turn(self, *args, **kwargs):
            self.calls.append({"args": args, "kwargs": kwargs})
            return {"turn": {"id": "turn-plan"}}

    backend = FakeBackend()
    controller._codex_backend = backend
    controller._codex_thread_id = "thread-plan"
    controller._codex_thread_mode = "interviewer"
    controller._ensure_codex_loop()
    blueprint = controller.service.roles.blueprint_for(
        "post_training_engineer", "new_grad"
    )
    questions = []
    for round_index, round_value in enumerate(blueprint.rounds):
        if round_value.type == "coding":
            continue
        for item_index in range(round_value.item_count):
            questions.append(
                {
                    "round_index": round_index,
                    "kind": round_value.type,
                    "title": f"Codex 计划 {round_index}-{item_index}",
                    "prompt": "请说明判断、证据和失败回退路径，并给出一个可验证的工程细节。",
                }
            )
    context = controller.personalizedInterviewPlanContext(
        "post_training_engineer", "new_grad", "medium", "", False
    )
    controller.generatePersonalizedInterviewPlanWithCodex(
        "post_training_engineer",
        "new_grad",
        "medium",
        "",
        False,
        context["context_sha256"],
    )
    assert _wait_for(lambda: len(backend.calls) == 1)
    assert backend.calls[0]["kwargs"]["output_schema"]["required"] == ["questions"]
    for event in (
        CodexEvent("turn/started", {"turnId": "turn-plan"}),
        CodexEvent(
            "item/agentMessage/delta",
            {"turnId": "turn-plan", "delta": json.dumps({"questions": questions})},
        ),
        CodexEvent("turn/completed", {"turnId": "turn-plan", "status": "completed"}),
    ):
        controller._handle_codex_event(event)
        QCoreApplication.processEvents()
    assert controller.interviewPlanPreview["status"] == "ready"
    assert controller.confirmPersonalizedInterviewPlan()
    session = controller.service.interview_session(
        "codex-plan-user", controller.interview["interview_id"]
    )
    assert session["ai_mode"] == "codex"
    controller.shutdown()


def test_controller_transcription_populates_editable_draft_without_locking(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="voice-user")
    controller.completeOnboarding(
        "voice-user", "ai_product_manager", "new_grad", "provider", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "provider"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
    question = controller.interview["question"]
    assert question["kind"] != "coding"

    audio = (
        profile_paths(root, "voice-user").interviews_root
        / controller.interview["interview_id"]
        / "audio"
        / "answer.wav"
    )
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"RIFF synthetic")
    recorder = controller._voice_recorder
    recorder.path = audio
    recorder.state = "recorded"
    connection = ProviderConfig(
        "voice-provider", "openai-compatible", "whisper", "Voice provider", "http://127.0.0.1:1/v1", None
    )

    class FakeTranscriber:
        async def transcribe(self, path, *, consent_remote, language):
            assert path == audio
            assert consent_remote is True
            assert language == "zh"
            return "这是可以继续编辑的转录草稿。"

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.list_connections",
        lambda repo_root, profile_id: (connection,),
    )
    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.OpenAICompatibleTranscriber",
        lambda config, api_key: FakeTranscriber(),
    )

    def synchronous_background(operation, complete, failed=None):
        try:
            complete(operation())
        except Exception as error:
            if failed:
                failed(str(error))
            else:
                raise

    monkeypatch.setattr(controller, "_background", synchronous_background)
    received: list[str] = []
    controller.interviewTranscriptReady.connect(received.append)
    controller.transcribeInterviewRecording(connection.connection_id, True)

    assert received == ["这是可以继续编辑的转录草稿。"]
    assert controller.interviewVoice["transcription_state"] == "transcribed"
    assert controller.interview.get("answer_locked") is False
    session = controller.service.interview_session(
        "voice-user", controller.interview["interview_id"]
    )
    assert session["answers"] == {}
    controller.shutdown()


def test_controller_transcription_rejects_without_remote_consent(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="voice-consent-user")
    controller.completeOnboarding(
        "voice-consent-user", "ai_product_manager", "new_grad", "provider", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "provider"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
    audio = (
        profile_paths(root, "voice-consent-user").interviews_root
        / controller.interview["interview_id"]
        / "audio"
        / "answer.wav"
    )
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"wav")
    controller._voice_recorder.path = audio
    controller._voice_recorder.state = "recorded"
    called = False

    class UnexpectedTranscriber:
        def __init__(self, *args, **kwargs):
            nonlocal called
            called = True

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.OpenAICompatibleTranscriber",
        UnexpectedTranscriber,
    )
    connection = ProviderConfig(
        "voice-provider", "openai-compatible", "whisper", "Voice provider", "http://127.0.0.1:1/v1", None
    )
    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.list_connections",
        lambda repo_root, profile_id: (connection,),
    )
    errors: list[str] = []
    controller.toast.connect(errors.append)
    controller.transcribeInterviewRecording(connection.connection_id, False)
    assert not called
    assert errors and "授权" in errors[-1]
    controller.shutdown()


def test_late_transcription_for_previous_question_is_ignored(
    tmp_path: Path, qapp, monkeypatch: pytest.MonkeyPatch
) -> None:
    del qapp
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    root = _repository(tmp_path)
    controller = AppController(root, profile_id="voice-stale-user")
    controller.completeOnboarding(
        "voice-stale-user", "ai_product_manager", "new_grad", "provider", "{}"
    )
    controller.createConfiguredInterview(
        "ai_product_manager", "new_grad", "medium", "provider"
    )
    assert _wait_for(lambda: controller.interview.get("question") is not None)
    audio = (
        profile_paths(root, "voice-stale-user").interviews_root
        / controller.interview["interview_id"]
        / "audio"
        / "answer.wav"
    )
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"wav")
    controller._voice_recorder.path = audio
    controller._voice_recorder.state = "recorded"
    connection = ProviderConfig(
        "voice-provider", "openai-compatible", "whisper", "Voice provider", "http://127.0.0.1:1/v1", None
    )

    class FakeTranscriber:
        async def transcribe(self, path, *, consent_remote, language):
            return "late transcript"

    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.list_connections",
        lambda repo_root, profile_id: (connection,),
    )
    monkeypatch.setattr(
        "llm_interview_lab.desktop.controller.OpenAICompatibleTranscriber",
        lambda config, api_key: FakeTranscriber(),
    )
    pending: list[tuple[object, object, object]] = []

    def delayed_background(operation, complete, failed=None):
        pending.append((operation, complete, failed))

    monkeypatch.setattr(controller, "_background", delayed_background)
    received: list[str] = []
    controller.interviewTranscriptReady.connect(received.append)
    controller.transcribeInterviewRecording(connection.connection_id, True)
    assert pending
    original_question = controller.interview["question"]
    controller._interview["question"] = {**original_question, "question_id": "q-999"}
    _operation, complete, _failed = pending[0]
    complete("late transcript")
    assert received == []
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
    repository_job, desktop_jobs = workflow.split("  desktop-windows:", maxsplit=1)
    # Keep assertions scoped to the Windows job.  Release publishing is defined
    # after the desktop jobs and its dependency list legitimately mentions the
    # CPU PyTorch validation job.
    desktop_job, _ = desktop_jobs.split("  desktop-macos-arm64:", maxsplit=1)
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
    assert 'objectName: "codexModelEffortSummary"' in connections_qml
    assert 'objectName: "openCodexModelSettings"' in connections_qml
    assert 'text: "模型与推理强度"' in connections_qml
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
    assert 'return "继续面试"' in home

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


def test_progress_page_separates_mastery_from_evidence_coverage() -> None:
    progress = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/ProgressPage.qml"
    ).read_text(encoding="utf-8")

    assert "尚无评测证据" in progress
    assert "当前版本上限" in progress
    assert "当前版本尚无可评测资产" in progress
    assert "不表示你的能力为 0" in progress
    assert "不是 Offer 概率" in progress
    assert "modelData.assessed_mastery" in progress
    assert "modelData.assessment_coverage" in progress
    assert "modelData.verified" not in progress


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
    assert 'readonly property string focusKind:' in home
    assert ': activeInterview ? "interview"' in home
    assert ': currentPractice ? "practice"' in home
    assert ': actionableRetention ? "retention"' in home
    assert ': firstUnlock ? "unlock" : "empty"' in home
    assert 'id: evidenceRail' in home
    assert 'return "浏览可练题目"' in home
    assert 'StatusPill {' in home

    assert 'objectName: "learnProblemList"' in learn
    assert 'objectName: "learnOpenProblemButton"' in learn
    assert 'objectName: "knowledgeBrowserButton"' in learn
    assert 'objectName: "knowledgeBrowser"' in learn
    assert 'readonly property bool drillDownLayout:' in learn
    assert 'section === "courses" ? 0 : 1' in learn
    assert 'root.selectSection("knowledge")' in learn
    assert "maximumLineCount: 2" in learn
    assert 'modelData.skills.slice(0, 3).join(" · ")' in learn
    assert 'root.blockingReason(root.selectedProblem)' in learn
    assert 'root.app.openProblem(root.selectedProblem.problem_id)' in learn
    assert 'app.loadKnowledge()' in learn
    assert 'app.searchKnowledge(knowledgeQuery.text)' in learn
    assert 'app.openKnowledgeCard' in learn


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
    assert "root.configuration.non_coding_fallback" in interview
    assert "root.missingRoundLabel(rounds[i])" in interview
    assert "root.roundTypeText(item.round || item.type || \"\")" in interview
    assert "no_strict_candidate" in interview
    assert 'item.skills.join("、")' not in interview
    assert "root.assessmentSourceText(modelData.source)" in interview
    assert "root.confidenceText(modelData.confidence)" in interview
    assert 'rounds.join("、")' not in interview
    assert 'role.currentValue || "applied_ai_engineer"' not in interview
    assert 'objectName: "startNonCodingInterview"' in interview
    assert 'role.currentValue === "post_training_engineer"' not in interview
    assert 'seniority.currentValue === "new_grad"' not in interview
    assert 'difficulty.currentValue === "medium"' not in interview
    assert "求职材料（可选）" in interview
    assert 'objectName: "personalizedInterviewConnection"' in interview
    assert 'objectName: "personalizedInterviewAlphaScope"' in interview
    assert 'objectName: "personalizedInterviewContextDialog"' in interview
    assert 'objectName: "personalizedInterviewPlanDialog"' in interview
    assert 'objectName: "confirmPersonalizedInterviewPlan"' in interview
    assert 'objectName: "interviewVoiceCard"' in interview
    assert 'objectName: "startInterviewRecording"' in interview
    assert 'objectName: "stopInterviewRecording"' in interview
    assert 'objectName: "transcribeInterviewRecording"' in interview
    assert 'objectName: "interviewVoiceRemoteConsent"' in interview
    assert 'app.startInterviewRecording()' in interview
    assert 'app.stopInterviewRecording()' in interview
    assert 'app.transcribeInterviewRecording(' in interview
    assert 'function onInterviewTranscriptReady(value)' in interview
    # A transcript is deliberately inserted as an editable draft; it must
    # still go through the normal lock/submit action.
    assert 'answer.text = value || ""' in interview
    assert 'app.lockInterviewAnswer(value)' not in interview
    assert "app.dynamicInterviewContextPreview(" in interview
    assert "app.startDynamicPersonalizedInterview(" in interview
    assert "app.personalizedInterviewPlanContext(" not in interview
    assert "app.generatePersonalizedInterviewPlan(" not in interview
    assert "app.generatePersonalizedInterviewPlanWithCodex(" not in interview
    # Dynamic interviews enter on a local process opening and materialize only
    # the current turn.  The legacy plan dialog remains a compatibility object
    # but must never be opened by the current GUI path.
    assert 'app.interviewPlanPreview.plan_mode !== "dynamic_ai"' not in interview
    assert 'function onInterviewPlanReady()' in interview
    signal_body = interview.split('function onInterviewPlanReady()', 1)[1].split(
        'function onInterviewTranscriptReady', 1
    )[0]
    assert '.open()' not in signal_body
    assert 'startDynamicPersonalizedInterview(' in interview
    assert '正在准备第一问' not in interview
    dialog_body = interview.split('objectName: "personalizedInterviewContextDialog"', 1)[1].split(
        'objectName: "personalizedInterviewPlanDialog"', 1
    )[0]
    assert 'StatusPill {' not in dialog_body
    assert 'ContextPreviewList {' in dialog_body
    context_list = (REPO_ROOT / "src/llm_interview_lab/desktop/qml/components/ContextPreviewList.qml").read_text(encoding="utf-8")
    assert 'height: rowContent.implicitHeight + 24' in context_list
    assert 'wrapMode: Text.Wrap' in context_list
    assert 'objectName: "personalizedInterviewCodexPreferences"' in interview
    assert 'objectName: "openCodexPreferencesFromInterview"' in interview
    assert 'text: "设置模型与推理强度"' in interview
    assert 'objectName: "personalizedInterviewMaterialAccessNotice"' in interview
    assert 'objectName: "openMaterialsForInterviewAuthorization"' in interview
    assert "app.setMaterialAiAccess(material.currentValue, true)" in interview
    assert 'objectName: "personalizedInterviewConsentNotice"' in interview
    assert "难度用于调整 AI 追问强度" in interview
    assert "高压设置不会阻止" not in interview  # no duplicate, misleading coding promise
    assert 'property bool codexPlanPending: false' in interview
    assert 'function onAiStateChanged()' in interview
    assert 'Qt.callLater(root.openPersonalizedPlanContext)' in interview
    assert 'app.navigate("settings")' in interview
    assert "outputSchema" not in interview  # schema stays in the controller
    assert "app.confirmPersonalizedInterviewPlan()" in interview
    assert 'visible: false' in interview
    assert interview.index('objectName: "startNonCodingInterview"') < interview.index(
        'objectName: "interviewPyTorchEnvironmentHelp"'
    )
    assert 'objectName: "nonCodingInterviewConfirmationDialog"' in interview
    assert 'title: "这不是完整岗位蓝图"' in interview
    assert 'height: Math.min(500, root.height - 48)' in interview
    assert 'id: fallbackDialogViewport' in interview
    assert 'contentHeight: fallbackDialogContent.implicitHeight' in interview
    assert 'footer: DialogButtonBox {' in interview
    assert 'alignment: Qt.AlignRight' in interview
    assert 'objectName: "nonCodingInterviewBackButton"' in interview
    assert 'text: "返回"' in interview
    assert 'objectName: "nonCodingInterviewConfirmButton"' in interview
    assert 'text: "确认开始专项"' in interview
    assert 'onOpened: fallbackBackButton.forceActiveFocus()' in interview
    assert "各轮仍保留原蓝图权重，不会重新归一化" in interview
    assert "始终标记为未完整，只形成部分面试证据" in interview
    assert "技术状态：incomplete / partial evidence" in interview
    assert "专项结果不会改变 Practice mastery" in interview
    assert "root.fallbackRoundSummary(root.nonCodingFallback().included_rounds)" in interview
    assert "root.fallbackRoundSummary(root.nonCodingFallback().omitted_rounds)" in interview
    assert "root.nonCodingFallback().duration_minutes" in interview
    assert "root.fallbackCoveragePercent()" in interview
    assert 'app.createNonCodingInterview(' in interview
    assert 'useMaterial.checked ? material.currentValue : ""' in interview
    assert 'useMaterial.checked ? consent.checked : false' in interview
    assert 'python -m pip install -e \\".[torch,dev]\\"' in interview
    assert "桌面应用不会自行安装依赖" in interview
    assert "需先克隆源码并进入仓库根目录" in interview
    assert 'objectName: "interviewSourceEnvironmentLink"' in interview
    assert 'objectName: "interviewFallbackSourceEnvironmentLink"' in interview
    assert "https://github.com/ComistryMo/llm_interview_lab/blob/main/docs/desktop-app.md" in interview
    assert "Qt.openUrlExternally(link)" in interview
    assert "当前环境暂缺所需依赖；可先切换到“标准”或查看环境说明。" not in interview
    assert "范围  非代码专项（部分证据）" in interview
    assert 'objectName: "interviewFallbackResultScope"' in interview
    assert "非代码专项 · 蓝图证据覆盖 " in interview
    assert "省略代码实现轮次：" in interview
    assert "root.interviewResult.blueprint_coverage" in interview

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
    assert "不改变刷题训练的掌握状态" in interview
    assert 'font.family: "Cascadia Mono, Consolas, monospace"' not in interview


def test_no_ai_interview_setup_explains_the_ai_boundary() -> None:
    interview = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/InterviewPage.qml"
    ).read_text(encoding="utf-8")
    assert 'objectName: "noAiInterviewNotice"' in interview
    assert "模拟面试需要 AI" in interview
    assert "No-AI 模式仍可继续刷题、运行测试、复盘和间隔复测" in interview
    assert 'objectName: "goToConnectionsFromInterview"' in interview
    assert 'onClicked: app.navigate("connections")' in interview
    # The legacy fallback controls remain in the file for compatibility, but
    # the UI must not start a session while No-AI is selected.
    assert 'aiMode.currentValue !== "disabled"' in interview


def test_material_import_explains_pdf_docx_text_snapshot_capability() -> None:
    career = (
        REPO_ROOT / "src/llm_interview_lab/desktop/qml/pages/CareerPage.qml"
    ).read_text(encoding="utf-8")
    assert 'readonly property bool selectedOpaqueMaterial' in career
    assert 'objectName: "materialAiCapabilityNotice"' in career
    assert "文本型 PDF" in career
    assert "DOCX 会提取" in career
    assert "文本快照" in career
    assert "aiAccess.checked" in career


    assert 'objectName: "materialAiAccessToggle"' in career
    assert "app.setMaterialAiAccess(modelData.id, desired)" in career


@pytest.mark.parametrize("page", ["home", "learn", "exercise", "interview"])
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
