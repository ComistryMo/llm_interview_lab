"""Qt-facing controller that delegates all domain work to ApplicationService."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QRunnable, QSettings, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from ..ai.codex_backend import CodexAppServerBackend, CodexEvent, discover_codex_executable
from ..ai.connections import (
    ConnectionConfigError,
    delete_connection,
    list_connections,
    save_connection,
)
from ..ai.context_builder import (
    build_practice_context_preview,
    build_role_interview_context_preview,
)
from ..ai.credentials import CredentialError, KeyringCredentialStore
from ..ai.providers import create_chat_provider
from ..application import ApplicationService
from ..lifecycle import ReviewInput
from ..workspace import ensure_profile_path_is_safe, profile_paths, validate_profile_id
from .i18n import friendly_error, localize_role, text
from .runtime import is_packaged_desktop, migrate_legacy_desktop_data


class WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class Worker(QRunnable):
    def __init__(self, operation: Callable[[], Any]) -> None:
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.completed.emit(self.operation())
        except Exception as error:  # UI boundary: domain errors are already sanitized.
            self.signals.failed.emit(str(error))


def _decode_ai_assessment(
    text: str, dimensions: set[str], fatal_issues: set[str]
) -> dict[str, Any]:
    """Validate provider JSON; polished prose alone never becomes a score."""

    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("AI interviewer did not return the required JSON scorecard")
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise RuntimeError("AI interviewer returned invalid JSON") from error
    if not isinstance(value, dict) or set(value) != {
        "scores",
        "evidence",
        "confidence",
        "fatal_issues",
        "follow_up",
    }:
        raise RuntimeError("AI scorecard fields do not match the public rubric contract")
    scores = value["scores"]
    if not isinstance(scores, dict) or set(scores) != dimensions:
        raise RuntimeError("AI scorecard dimensions do not match the frozen rubric")
    if any(type(score) is not int or score < 1 or score > 5 for score in scores.values()):
        raise RuntimeError("AI rubric scores must be integers from 1 to 5")
    evidence = value["evidence"]
    if not isinstance(evidence, str) or not (20 <= len(evidence.strip()) <= 4000):
        raise RuntimeError("AI scorecard must cite concise answer evidence")
    if value["confidence"] not in {"low", "medium", "high"}:
        raise RuntimeError("AI scorecard confidence is invalid")
    fatal = value["fatal_issues"]
    if not isinstance(fatal, list) or any(item not in fatal_issues for item in fatal):
        raise RuntimeError("AI scorecard contains an unknown fatal issue")
    follow_up = value["follow_up"]
    if not isinstance(follow_up, str) or len(follow_up) > 2000:
        raise RuntimeError("AI follow-up is invalid")
    value["evidence"] = evidence.strip()
    value["follow_up"] = follow_up.strip()
    return value


def _demo_dashboard() -> dict[str, Any]:
    return {
        "profile_id": "demo",
        "role": {
            "primary_role": "ai_algorithm_research_engineer",
            "title": "AI Algorithm / Research Engineer",
            "seniority": "new_grad",
            "ai_mode": "disabled",
        },
        "current": {"problem_id": "LOSS-014", "title": "Cross Entropy", "status": "in_progress"},
        "recommended_quests": [
            {"id": "tensor_stable_loss", "title": "Tensor & Stable Loss"},
            {"id": "optimizer_training", "title": "Optimizer & Training Loop"},
        ],
        "due_review": ["TNS-011"],
        "due_retention": [{"problem_id": "LOSS-007", "stage": "d7", "due_at": "2026-08-28"}],
        "unlocks": [{"problem_id": "OPT-001", "title": "SGD"}],
        "mastered_count": 14,
        "role_readiness": [
            {"id": "python_engineering", "label": "Python Engineering", "self_reported": 0.75, "verified": 0.62},
            {"id": "deep_learning", "label": "Deep Learning", "self_reported": 0.65, "verified": 0.48},
            {"id": "llm_vlm", "label": "LLM / VLM", "self_reported": 0.55, "verified": 0.36},
            {"id": "system_design", "label": "System Design", "self_reported": 0.45, "verified": 0.18},
        ],
    }


class AppController(QObject):
    stateChanged = Signal()
    busyChanged = Signal()
    pageChanged = Signal()
    toast = Signal(str)
    aiDelta = Signal(str)
    aiStateChanged = Signal()
    codexApproval = Signal("QVariantMap")

    def __init__(
        self,
        repo_root: Path,
        *,
        profile_id: str = "default",
        demo_page: str | None = None,
        service: ApplicationService | None = None,
        legacy_data_root: Path | None = None,
        log_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.repo_root = repo_root.resolve()
        self.service = service or ApplicationService(self.repo_root)
        self._profile_id = profile_id
        self._page = demo_page or "home"
        self._onboarding = False
        self._dashboard: dict[str, Any] = {}
        self._problems: list[dict[str, Any]] = []
        self._current_task: dict[str, Any] = {}
        self._submission = ""
        self._test_output = ""
        self._interview: dict[str, Any] = {}
        self._connections: list[dict[str, Any]] = []
        self._materials: list[dict[str, Any]] = []
        self._pending_ai_assessment: dict[str, Any] | None = None
        self._busy = False
        self._ai_status = text("status.ai_offline")
        self._workers: set[Worker] = set()
        self._thread_pool = QThreadPool.globalInstance()
        self._settings = QSettings("ComistryMo", "LLMInterviewLab")
        self._theme = str(self._settings.value("theme", "system"))
        self._font_scale = float(self._settings.value("fontScale", 1.0))
        self._codex_executable = str(self._settings.value("codexExecutable", ""))
        self._legacy_data_root = legacy_data_root.resolve() if legacy_data_root else None
        self._legacy_migration_dismissed = False
        self._log_root = (log_root or (self.repo_root / "logs")).resolve()
        self._codex_loop: asyncio.AbstractEventLoop | None = None
        self._codex_thread: threading.Thread | None = None
        self._codex_backend: CodexAppServerBackend | None = None
        self._codex_thread_id: str | None = None
        self._codex_turn_id: str | None = None
        self._codex_diff = ""
        self._shutdown_done = False
        if demo_page:
            self._load_demo(demo_page)
        else:
            self.refresh()

    def _load_demo(self, page: str) -> None:
        self._profile_id = "demo"
        self._onboarding = page == "onboarding"
        self._dashboard = _demo_dashboard()
        self._problems = [
            {"problem_id": "TNS-011", "title": "Last Valid Token", "status": "mastered", "validation": "oracle", "locked": False, "retention": True},
            {"problem_id": "LOSS-014", "title": "Cross Entropy", "status": "in_progress", "validation": "oracle", "locked": False, "retention": True},
            {"problem_id": "ATT-002", "title": "Scaled Dot-Product Attention", "status": "not_started", "validation": "oracle", "locked": True, "retention": False},
        ]
        self._current_task = {
            "problem_id": "LOSS-014",
            "title": "Cross Entropy",
            "task": "Implement numerically stable cross entropy for batched logits.\n\nInput shape: logits [B, C], targets [B].",
        }
        self._submission = "def cross_entropy(logits, targets):\n    # Your implementation\n    raise NotImplementedError\n"
        self._test_output = "尚未运行公开测试。"
        self._interview = {
            "interview_id": "role-interview-demo",
            "status": "active",
            "role_id": "applied_ai_engineer",
            "role_title": "Applied AI Engineer",
            "seniority": "new_grad",
            "ai_mode": "provider",
            "material_refs": [],
            "remaining_seconds": 3120,
            "question": {
                "question_id": "q-002",
                "kind": "system_design",
                "title": "Design a Reliable Tool-Calling Assistant",
                "prompt": "Design validation, execution, retry, timeout, observability and fallback for a production tool-calling assistant.",
                "rubric": {"dimensions": {"failure_handling": {}, "tradeoffs": {}, "evaluation": {}}},
            },
        }
        self._connections = [
            {"connection_id": "ollama-local", "provider_id": "ollama", "display_name": "本地 Ollama", "model": "qwen", "status": "尚未测试"},
        ]
        self._materials = [
            {
                "id": "resume-demo",
                "kind": "resume",
                "title": "Synthetic candidate resume",
                "sha256": "4" * 64,
                "size_bytes": 512,
                "relative_path": "materials/files/resume-demo.md",
                "tags": ["synthetic"],
                "ai_access": True,
            }
        ]
        self._localize_dashboard()

    @Property(str, notify=stateChanged)
    def profileId(self) -> str:
        return self._profile_id

    @Property(bool, notify=stateChanged)
    def onboardingRequired(self) -> bool:
        return self._onboarding

    @Property("QVariantList", notify=stateChanged)
    def roles(self) -> list[dict[str, Any]]:
        return [localize_role(card) for card in self.service.role_cards()]

    @Property("QVariantMap", notify=stateChanged)
    def dashboard(self) -> dict[str, Any]:
        return self._dashboard

    @Property("QVariantList", notify=stateChanged)
    def problems(self) -> list[dict[str, Any]]:
        return self._problems

    @Property("QVariantMap", notify=stateChanged)
    def currentTask(self) -> dict[str, Any]:
        return self._current_task

    @Property(str, notify=stateChanged)
    def submissionText(self) -> str:
        return self._submission

    @Property(str, notify=stateChanged)
    def testOutput(self) -> str:
        return self._test_output

    @Property("QVariantMap", notify=stateChanged)
    def interview(self) -> dict[str, Any]:
        return self._interview

    @Property("QVariantList", notify=stateChanged)
    def connections(self) -> list[dict[str, Any]]:
        return self._connections

    @Property("QVariantList", constant=True)
    def providerOptions(self) -> list[str]:
        """Expose only adapters shipped by the current distribution."""

        if is_packaged_desktop():
            return ["openai", "openai-compatible", "ollama"]
        return ["openai", "openai-compatible", "ollama", "anthropic", "gemini"]

    @Property("QVariantList", notify=stateChanged)
    def materials(self) -> list[dict[str, Any]]:
        return self._materials

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=pageChanged)
    def currentPage(self) -> str:
        return self._page

    @Property(str, notify=stateChanged)
    def theme(self) -> str:
        return self._theme

    @Property(float, notify=stateChanged)
    def fontScale(self) -> float:
        return self._font_scale

    @Property(str, notify=aiStateChanged)
    def aiStatus(self) -> str:
        return self._ai_status

    @Property(bool, notify=aiStateChanged)
    def codexAvailable(self) -> bool:
        return discover_codex_executable(self._codex_executable or None) is not None

    @Property(str, notify=stateChanged)
    def dataDirectory(self) -> str:
        return str(self.repo_root)

    @Property(str, notify=stateChanged)
    def logDirectory(self) -> str:
        return str(self._log_root)

    @Property(str, notify=stateChanged)
    def codexExecutable(self) -> str:
        return self._codex_executable

    @Property(bool, notify=stateChanged)
    def legacyMigrationAvailable(self) -> bool:
        return self._legacy_data_root is not None and not self._legacy_migration_dismissed

    @Property(str, notify=stateChanged)
    def legacyDataDirectory(self) -> str:
        return str(self._legacy_data_root) if self._legacy_data_root else ""

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        return text(key)

    def _show_error(self, error: BaseException | str) -> None:
        self.toast.emit(friendly_error(error))

    def _localize_dashboard(self) -> None:
        role = self._dashboard.get("role")
        if isinstance(role, dict) and role.get("primary_role"):
            localized = localize_role({"id": role["primary_role"]})
            role["title"] = localized.get("title", role.get("title", ""))

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _background(self, operation: Callable[[], Any], complete: Callable[[Any], None]) -> None:
        self._set_busy(True)
        worker = Worker(operation)
        self._workers.add(worker)

        def done(value: Any) -> None:
            self._workers.discard(worker)
            self._set_busy(False)
            complete(value)

        def failed(message: str) -> None:
            self._workers.discard(worker)
            self._set_busy(False)
            self._show_error(message)

        worker.signals.completed.connect(done)
        worker.signals.failed.connect(failed)
        self._thread_pool.start(worker)

    @Slot(str)
    def navigate(self, page: str) -> None:
        if page not in {
            "home",
            "career",
            "learn",
            "exercise",
            "interview",
            "coach",
            "progress",
            "connections",
            "settings",
        }:
            return
        self._page = page
        self.pageChanged.emit()

    @Slot()
    def refresh(self) -> None:
        path = profile_paths(self.repo_root, self._profile_id).profile_file
        if not path.is_file():
            self._onboarding = True
            self._dashboard = {}
            self._problems = []
            self._connections = []
            self._materials = []
            self.stateChanged.emit()
            return
        try:
            self._dashboard = self.service.dashboard(self._profile_id)
            self._localize_dashboard()
            self._problems = self.service.problem_cards(self._profile_id)
            current = self.service.current_submission(self._profile_id)
            if current:
                self._current_task = self.service.problem_view(current["problem_id"])
                self._submission = current["text"]
            self._connections = [
                {**config.__dict__, "status": "已保存，尚未测试"}
                for config in list_connections(self.repo_root, self._profile_id)
            ]
            self._materials = self.service.material_cards(self._profile_id)
            self._onboarding = False
        except Exception as error:
            self._show_error(error)
        self.stateChanged.emit()

    @Slot(str, str, str, str, str)
    def completeOnboarding(
        self,
        profile_id: str,
        role_id: str,
        seniority: str,
        ai_mode: str,
        assessment_json: str,
    ) -> None:
        try:
            validate_profile_id(profile_id)
            assessment = json.loads(assessment_json or "{}")
            self.service.initialize_profile(
                profile_id,
                role_id=role_id,
                seniority=seniority,
                skill_self_assessment=assessment,
                ai_mode=ai_mode,
            )
            self._profile_id = profile_id
            self._onboarding = False
            self.refresh()
            if self._dashboard.get("unlocks"):
                self.openProblem(self._dashboard["unlocks"][0]["problem_id"])
            else:
                self.navigate("home")
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, bool)
    def addMaterial(
        self, source_url: str, kind: str, title: str, ai_access: bool
    ) -> None:
        if self._profile_id == "demo":
            self.toast.emit("演示材料完全虚构且为只读。")
            return
        try:
            source = (
                QUrl(source_url).toLocalFile()
                if source_url.startswith("file:")
                else source_url
            )
            self.service.add_career_material(
                self._profile_id,
                source,
                kind=kind,
                title=title or None,
                ai_access=ai_access,
            )
            self.refresh()
            self.toast.emit("材料已复制到本地学习档案，Git 默认忽略该目录。")
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def openProblem(self, problem_id: str) -> None:
        try:
            current = self.service.current_submission(self._profile_id)
            if current is None or current["problem_id"] != problem_id:
                self.service.start_practice(self._profile_id, problem_id)
                current = self.service.current_submission(self._profile_id)
            assert current is not None
            self._current_task = self.service.problem_view(problem_id)
            self._submission = current["text"]
            self._test_output = "可以开始：完成本次作答后运行公开测试。"
            self._page = "exercise"
            self.stateChanged.emit()
            self.pageChanged.emit()
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def saveSubmission(self, text: str) -> None:
        if self._profile_id == "demo":
            self._submission = text
            self.stateChanged.emit()
            return
        try:
            current = self.service.current_submission(self._profile_id)
            if current is None:
                raise RuntimeError("no active submission")
            path = ensure_profile_path_is_safe(
                self.repo_root, self._profile_id, Path(current["path"]), must_exist=True
            )
            temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
            ensure_profile_path_is_safe(self.repo_root, self._profile_id, temporary)
            with temporary.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            self._submission = text
            self.toast.emit("已保存到本机。")
        except Exception as error:
            self._show_error(error)

    @Slot()
    def runTests(self) -> None:
        if not self._current_task:
            return
        if self._profile_id == "demo":
            self._test_output = "5 passed in 0.18s\n\n公开测试：PASS · 掌握状态：尚未达到"
            self.stateChanged.emit()
            return
        problem_id = self._current_task["problem_id"]

        def complete(result) -> None:
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"公开测试：{result.status.upper()} · 掌握状态：尚未达到"
            )
            self.stateChanged.emit()

        self._background(
            lambda: self.service.run_practice_tests(self._profile_id, problem_id),
            complete,
        )

    @Slot()
    def submitCurrent(self) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("演示模式不会记录提交。")
            return
        try:
            result = self.service.submit_practice(
                self._profile_id, self._current_task["problem_id"]
            )
            self.toast.emit(
                "实现已通过；仍需完成契约审查和口述答辩。"
                if result["implemented"]
                else "提交已记录，但当前公开测试尚未通过。"
            )
            self.refresh()
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, bool, bool)
    def reviewCurrent(
        self,
        explanation: str,
        complexity: str,
        boundaries: str,
        contract_passed: bool,
        oral_passed: bool,
    ) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("请先在真实学习档案中开始一道题。")
            return
        try:
            result = self.service.review_practice(
                self._profile_id,
                self._current_task["problem_id"],
                ReviewInput(
                    contract_status="passed" if contract_passed else "failed",
                    oral_status="passed" if oral_passed else "failed",
                    code_explanation=explanation,
                    complexity=complexity,
                    boundary_conditions=boundaries,
                ),
            )
            self.toast.emit(
                f"审查已记录：{result.status}。是否掌握仍由确定性学习流程判定。"
            )
            self.refresh()
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def startRetentionStage(self, stage: str) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("请先完成该题的实现与审查。")
            return
        try:
            problem_id = self._current_task["problem_id"]
            result = self.service.start_retention(self._profile_id, problem_id, stage)
            current = self.service.current_submission(self._profile_id)
            if current is None:
                raise RuntimeError("retention attempt was not created")
            self._submission = current["text"]
            self._test_output = (
                f"{stage.upper()} 复测尝试 {result['attempt_id']} 独立创建；"
                "系统没有复制上一次答案。"
            )
            self.stateChanged.emit()
            self.toast.emit(f"已开始经过验证的 {stage.upper()} 间隔复测。")
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str)
    def createInterview(self, role_id: str, seniority: str, difficulty: str) -> None:
        if self._profile_id == "demo":
            self._page = "interview"
            self.pageChanged.emit()
            return
        try:
            session = self.service.create_interview(
                self._profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
            )
            self.service.start_interview(self._profile_id, session["interview_id"])
            self._load_interview(session["interview_id"])
            self.navigate("interview")
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, str)
    def createConfiguredInterview(
        self, role_id: str, seniority: str, difficulty: str, ai_mode: str
    ) -> None:
        if ai_mode == "disabled":
            self.createInterview(role_id, seniority, difficulty)
            return
        if self._profile_id == "demo":
            self._page = "interview"
            self.pageChanged.emit()
            return
        try:
            session = self.service.create_interview(
                self._profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
                ai_mode=ai_mode,
            )
            self.service.start_interview(self._profile_id, session["interview_id"])
            self._load_interview(session["interview_id"])
            self.navigate("interview")
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, str, bool, str)
    def createTailoredInterview(
        self,
        role_id: str,
        seniority: str,
        difficulty: str,
        material_id: str,
        consent: bool,
        ai_mode: str,
    ) -> None:
        if self._profile_id == "demo":
            self._page = "interview"
            self.pageChanged.emit()
            return
        try:
            session = self.service.create_interview(
                self._profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
                ai_mode=ai_mode,
                material_ids=(material_id,),
                consent_materials=consent,
            )
            self.service.start_interview(self._profile_id, session["interview_id"])
            self._load_interview(session["interview_id"])
            self.navigate("interview")
        except Exception as error:
            self._show_error(error)

    def _load_interview(self, interview_id: str) -> None:
        current = self.service.current_interview(self._profile_id, interview_id)
        session = self.service.interview_session(self._profile_id, interview_id)
        self._interview = {
            "interview_id": interview_id,
            "status": session["status"],
            "role_id": session["role_id"],
            "role_title": next(
                (
                    role["title"]
                    for role in self.service.role_cards()
                    if role["id"] == session["role_id"]
                ),
                session["role_id"].replace("_", " ").title(),
            ),
            "seniority": session["seniority"],
            "ai_mode": session["ai_mode"],
            "material_refs": session["material_refs"],
            **current,
        }
        question = current.get("question")
        if question and question.get("kind") == "coding":
            coding = self.service.current_interview_coding_submission(
                self._profile_id, interview_id
            )
            self._interview["coding_text"] = coding["text"]
        self.stateChanged.emit()

    @Slot(str)
    def saveInterviewCoding(self, text: str) -> None:
        if self._profile_id == "demo":
            self._interview["coding_text"] = text
            self.stateChanged.emit()
            return
        try:
            self.service.save_interview_coding_submission(
                self._profile_id, self._interview["interview_id"], text
            )
            self._interview["coding_text"] = text
            self.toast.emit("回答已保存到本机的本场面试记录。")
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def runInterviewCoding(self, text: str) -> None:
        if self._profile_id == "demo":
            self._test_output = "4 passed in 0.16s\n\n代码证据：PASS"
            self.stateChanged.emit()
            return
        try:
            self.service.save_interview_coding_submission(
                self._profile_id, self._interview["interview_id"], text
            )
        except Exception as error:
            self._show_error(error)
            return

        def complete(result) -> None:
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"代码证据：{result.status.upper()}"
            )
            self.stateChanged.emit()

        self._background(
            lambda: self.service.test_interview_coding(
                self._profile_id, self._interview["interview_id"]
            ),
            complete,
        )

    @Slot()
    def recordInterviewCodingRound(self) -> None:
        if self._profile_id == "demo":
            self.toast.emit("演示代码环节已记录。")
            return
        question = self._interview.get("question")
        if not question or question.get("kind") != "coding":
            return
        try:
            session = self.service.interview_session(
                self._profile_id, self._interview["interview_id"]
            )
            evidence = session["coding_evidence"].get(question["question_id"])
            if evidence is None:
                raise RuntimeError("run the interview grader before recording this round")
            passed = evidence["status"] == "passed"
            self.service.score_interview(
                self._profile_id,
                self._interview["interview_id"],
                question["question_id"],
                {"correctness": 5 if passed else 1},
                evidence=(
                    f"Local grader status={evidence['status']}; passed={evidence['passed']}; "
                    f"failed={evidence['failed']}; duration_ms={evidence['duration_ms']}"
                ),
                source="human",
                confidence="high",
                fatal_issues=() if passed else ("does_not_run",),
            )
            self._load_interview(self._interview["interview_id"])
        except Exception as error:
            self._show_error(error)

    @Slot(str, int, str)
    def answerInterview(self, answer: str, score: int, evidence: str) -> None:
        question = self._interview.get("question")
        scores = (
            {name: score for name in question["rubric"]["dimensions"]}
            if question
            else {}
        )
        self._record_manual_interview_assessment(answer, scores, evidence)

    @Slot(str, str, str)
    def answerInterviewDetailed(
        self, answer: str, scores_json: str, evidence: str
    ) -> None:
        try:
            scores = json.loads(scores_json)
        except (TypeError, json.JSONDecodeError):
            self.toast.emit("人工评分不符合当前 Rubric，请检查各维度分数。")
            return
        self._record_manual_interview_assessment(answer, scores, evidence)

    def _record_manual_interview_assessment(
        self, answer: str, scores: Any, evidence: str
    ) -> None:
        if self._profile_id == "demo":
            self.toast.emit("演示回答已在本次预览中记录。")
            return
        question = self._interview.get("question")
        if not question:
            return
        try:
            interview_id = self._interview["interview_id"]
            expected = set(question["rubric"]["dimensions"])
            if (
                not isinstance(scores, dict)
                or set(scores) != expected
                or any(type(value) is not int or not 1 <= value <= 5 for value in scores.values())
            ):
                raise RuntimeError("score every rubric dimension from 1 to 5")
            session = self.service.interview_session(self._profile_id, interview_id)
            if question["question_id"] not in session["answers"]:
                self.service.answer_interview(
                    self._profile_id, interview_id, question["question_id"], answer
                )
            self.service.score_interview(
                self._profile_id,
                interview_id,
                question["question_id"],
                scores,
                evidence=evidence,
                source="self",
                confidence="medium",
            )
            self._load_interview(interview_id)
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, bool)
    def assessInterviewWithProvider(
        self, answer: str, connection_id: str, include_materials: bool = True
    ) -> None:
        question = self._interview.get("question")
        if not question or question.get("kind") == "coding":
            return
        if self._profile_id == "demo":
            self.toast.emit("演示 AI 评分需要证据；不会改变刷题掌握状态。")
            return
        interview_id = self._interview["interview_id"]
        question_id = question["question_id"]
        dimensions = set(question["rubric"]["dimensions"])
        fatal_issues = set(question["rubric"]["fatal_issues"])

        def operation() -> dict[str, Any]:
            config = next(
                item
                for item in list_connections(self.repo_root, self._profile_id)
                if item.connection_id == connection_id
            )
            key = (
                KeyringCredentialStore().load(config.key_reference)
                if config.key_reference
                else None
            )
            preview = build_role_interview_context_preview(
                self.repo_root,
                self._profile_id,
                interview_id,
                candidate_answer=answer,
                include_materials=include_materials,
            )
            provider = create_chat_provider(config, api_key=key)
            instruction = (
                "Return JSON only with exactly these fields: scores (one integer 1-5 for "
                f"each of {sorted(dimensions)}), evidence (a quote or precise reference to "
                "the candidate answer), confidence (low|medium|high), fatal_issues (only "
                f"from {sorted(fatal_issues)}), and follow_up (one concise adaptive question "
                "or an empty string). Do not infer missing career facts."
            )

            async def collect() -> str:
                chunks: list[str] = []
                async for event in provider.stream_chat(
                    [
                        {"role": "system", "content": preview.selected_text},
                        {"role": "user", "content": instruction},
                    ]
                ):
                    if event.text:
                        chunks.append(event.text)
                return "".join(chunks)

            return _decode_ai_assessment(
                asyncio.run(collect()), dimensions, fatal_issues
            )

        def complete(result: dict[str, Any]) -> None:
            try:
                self.service.answer_interview(
                    self._profile_id, interview_id, question_id, answer
                )
                if result["follow_up"]:
                    self._pending_ai_assessment = {
                        **result,
                        "interview_id": interview_id,
                        "question_id": question_id,
                    }
                    self._interview["pending_followup"] = result["follow_up"]
                    self.stateChanged.emit()
                    return
                self.service.score_interview(
                    self._profile_id,
                    interview_id,
                    question_id,
                    result["scores"],
                    evidence=result["evidence"],
                    source="ai",
                    confidence=result["confidence"],
                    fatal_issues=result["fatal_issues"],
                )
                self._load_interview(interview_id)
            except Exception as error:
                self._show_error(error)

        self._background(operation, complete)

    @Slot(str)
    def answerAIFollowup(self, answer: str) -> None:
        pending = self._pending_ai_assessment
        if pending is None:
            return
        try:
            self.service.record_interview_followup(
                self._profile_id,
                pending["interview_id"],
                parent_question_id=pending["question_id"],
                prompt=pending["follow_up"],
                answer=answer,
            )
            self.service.score_interview(
                self._profile_id,
                pending["interview_id"],
                pending["question_id"],
                pending["scores"],
                evidence=pending["evidence"],
                source="ai",
                confidence=pending["confidence"],
                fatal_issues=pending["fatal_issues"],
            )
            interview_id = pending["interview_id"]
            self._pending_ai_assessment = None
            self._load_interview(interview_id)
        except Exception as error:
            self._show_error(error)

    @Slot()
    def finishInterview(self) -> None:
        if self._profile_id == "demo":
            self.toast.emit("演示报告：76/100；刷题训练的掌握状态不会改变。")
            return
        try:
            session = self.service.finish_interview(
                self._profile_id,
                self._interview["interview_id"],
                summary="本地结构化模拟面试已完成。",
                confirm_incomplete=True,
            )
            self._interview = session
            self.stateChanged.emit()
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, str, str, str)
    def saveConnection(
        self,
        connection_id: str,
        provider_id: str,
        model: str,
        display_name: str,
        base_url: str,
        api_key: str,
    ) -> None:
        try:
            save_connection(
                self.repo_root,
                self._profile_id,
                connection_id=connection_id,
                provider_id=provider_id,
                model=model,
                display_name=display_name,
                base_url=base_url or None,
                api_key=api_key or None,
            )
            self.refresh()
            self.toast.emit("连接已保存；API Key 仅存入系统密钥环。")
        except (ConnectionConfigError, CredentialError) as error:
            self._show_error(error)

    @Slot(str)
    def deleteConnection(self, connection_id: str) -> None:
        try:
            delete_connection(self.repo_root, self._profile_id, connection_id)
            self.refresh()
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def testConnection(self, connection_id: str) -> None:
        if self._profile_id == "demo":
            self.toast.emit("虚构演示连接检查完成。")
            return

        def operation():
            config = next(
                item
                for item in list_connections(self.repo_root, self._profile_id)
                if item.connection_id == connection_id
            )
            key = (
                KeyringCredentialStore().load(config.key_reference)
                if config.key_reference
                else None
            )
            return asyncio.run(
                create_chat_provider(config, api_key=key).test_connection()
            )

        def complete(result) -> None:
            for item in self._connections:
                if item["connection_id"] == connection_id:
                    item["status"] = "已连接" if result.ok else "连接失败"
            self.stateChanged.emit()
            self.toast.emit("连接成功。" if result.ok else friendly_error(result.message))

        self._background(operation, complete)

    def _practice_context_preview(
        self,
        mode: str,
        *,
        help_level: str | None,
        include_submission: bool,
        include_test_output: bool,
    ) -> dict[str, Any]:
        if self._profile_id == "demo":
            return {
                "estimated_tokens": 286,
                "parts": [
                    {"id": "policy", "label": "AI 行为规则", "selected": True, "sensitive": False},
                    {"id": "task", "label": "当前公开题面", "selected": True, "sensitive": False},
                    {"id": "submission", "label": "选中的当前答案", "selected": include_submission, "sensitive": True},
                    {"id": "test", "label": "最近公开测试摘要", "selected": include_test_output, "sensitive": False},
                ],
            }
        try:
            preview = build_practice_context_preview(
                self.repo_root,
                self.service.catalog,
                self._profile_id,
                mode=mode,
                help_level=help_level if mode == "teacher" else None,
                include_submission=include_submission,
                include_test_output=include_test_output,
            )
            return {
                "estimated_tokens": preview.estimated_tokens,
                "parts": [
                    {
                        "id": part.id,
                        "label": part.label,
                        "selected": part.selected,
                        "sensitive": part.sensitive,
                        "sha256": part.sha256,
                    }
                    for part in preview.parts
                ],
            }
        except Exception as error:
            self._show_error(error)
            return {"estimated_tokens": 0, "parts": []}

    @Slot(str, bool, result="QVariantMap")
    def contextPreview(self, mode: str, include_submission: bool) -> dict[str, Any]:
        """Backward-compatible preview used by early desktop clients."""

        return self._practice_context_preview(
            mode,
            help_level="H2" if mode == "teacher" else None,
            include_submission=include_submission,
            include_test_output=True,
        )

    @Slot(str, str, bool, bool, result="QVariantMap")
    def practiceContextPreview(
        self,
        mode: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> dict[str, Any]:
        return self._practice_context_preview(
            mode,
            help_level=help_level or None,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    @Slot(str, bool, result="QVariantMap")
    def interviewContextPreview(
        self, answer: str, include_materials: bool
    ) -> dict[str, Any]:
        if self._profile_id == "demo":
            return {
                "estimated_tokens": 244,
                "parts": [
                    {"id": "policy", "label": "Interviewer policy", "selected": True, "sensitive": False},
                    {"id": "question", "label": "Frozen question and rubric", "selected": True, "sensitive": False},
                    {"id": "candidate_answer", "label": "Candidate answer", "selected": True, "sensitive": True},
                ],
            }
        try:
            preview = build_role_interview_context_preview(
                self.repo_root,
                self._profile_id,
                self._interview["interview_id"],
                candidate_answer=answer,
                include_materials=include_materials,
            )
            return {
                "estimated_tokens": preview.estimated_tokens,
                "parts": [
                    {
                        "id": part.id,
                        "label": part.label,
                        "selected": part.selected,
                        "sensitive": part.sensitive,
                        "sha256": part.sha256,
                    }
                    for part in preview.parts
                ],
            }
        except Exception as error:
            self._show_error(error)
            return {"estimated_tokens": 0, "parts": []}

    @Slot(str, str, bool)
    def sendProviderMessage(self, connection_id: str, message: str, include_submission: bool) -> None:
        self.sendProviderPracticeMessage(
            connection_id, message, "coach", "", include_submission, True
        )

    @Slot(str, str, str, str, bool, bool)
    def sendProviderPracticeMessage(
        self,
        connection_id: str,
        message: str,
        mode: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> None:
        def operation() -> str:
            config = next(
                item for item in list_connections(self.repo_root, self._profile_id)
                if item.connection_id == connection_id
            )
            key = KeyringCredentialStore().load(config.key_reference) if config.key_reference else None
            preview = build_practice_context_preview(
                self.repo_root,
                self.service.catalog,
                self._profile_id,
                mode=mode,
                help_level=help_level if mode == "teacher" else None,
                include_submission=include_submission,
                include_test_output=include_test_output,
            )
            provider = create_chat_provider(config, api_key=key)

            async def collect() -> str:
                chunks: list[str] = []
                async for event in provider.stream_chat(
                    [
                        {"role": "system", "content": preview.selected_text},
                        {"role": "user", "content": message},
                    ]
                ):
                    if event.text:
                        chunks.append(event.text)
                        self.aiDelta.emit(event.text)
                return "".join(chunks)

            return asyncio.run(collect())

        self._background(operation, lambda _: self.toast.emit("AI 回答完成。"))

    def _ensure_codex_loop(self) -> asyncio.AbstractEventLoop:
        if self._codex_loop is not None:
            return self._codex_loop
        ready = threading.Event()

        def run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._codex_loop = loop
            ready.set()
            loop.run_forever()

        self._codex_thread = threading.Thread(target=run, name="llm-lab-codex", daemon=True)
        self._codex_thread.start()
        ready.wait(timeout=5)
        if self._codex_loop is None:
            raise RuntimeError("Codex event loop did not start")
        return self._codex_loop

    async def _pump_codex(self) -> None:
        assert self._codex_backend is not None
        async for event in self._codex_backend.events():
            if event.method == "item/agentMessage/delta":
                delta = event.params.get("delta", "")
                if isinstance(delta, str):
                    self.aiDelta.emit(delta)
            elif event.method == "item/fileChange/delta":
                delta = event.params.get("delta", "")
                if isinstance(delta, str):
                    # A bounded display buffer only. App Server remains the source
                    # of truth and the user must still approve the actual request.
                    self._codex_diff = (self._codex_diff + delta)[-100_000:]
            elif event.method == "turn/started":
                turn = event.params.get("turn", {})
                self._codex_turn_id = turn.get("id") or event.params.get("turnId")
                self._codex_diff = ""
            elif event.method == "turn/completed":
                self._ai_status = text("status.codex_ready")
                self.aiStateChanged.emit()
            elif event.requires_approval:
                params = event.params
                self.codexApproval.emit(
                    {
                        "request_id": str(event.request_id),
                        "action": event.method,
                        "scope": params.get("cwd", "当前仓库"),
                        "files": params.get("changes", []),
                        "diff": params.get("diff") or self._codex_diff,
                        "command": params.get("command", ""),
                        "reason": params.get("reason", "未提供原因"),
                        "risk": "该操作可能运行命令或修改文件。批准前请核对范围与 Diff。",
                    }
                )

    @Slot(str)
    def connectCodex(self, mode: str = "coach") -> None:
        try:
            loop = self._ensure_codex_loop()

            async def connect() -> None:
                self._codex_backend = CodexAppServerBackend(
                    self.repo_root,
                    executable=self._codex_executable or None,
                )
                await self._codex_backend.connect()
                account = await self._codex_backend.account()
                if account.get("account") is None:
                    raise RuntimeError("Codex is not signed in")
                response = await self._codex_backend.start_thread(mode=mode)
                self._codex_thread_id = response["thread"]["id"]
                self._ai_status = text("status.codex_connected")
                self.aiStateChanged.emit()
                asyncio.create_task(self._pump_codex())

            future = asyncio.run_coroutine_threadsafe(connect(), loop)
            future.add_done_callback(
                lambda value: self._show_error(value.exception()) if value.exception() else None
            )
        except Exception as error:
            self._show_error(error)

    @Slot(str)
    def sendCodexMessage(self, message: str) -> None:
        if self._codex_loop is None or self._codex_backend is None or not self._codex_thread_id:
            self.toast.emit("请先连接 Codex；也可以继续使用无需 AI 的本地功能。")
            return
        asyncio.run_coroutine_threadsafe(
            self._codex_backend.start_turn(self._codex_thread_id, message),
            self._codex_loop,
        )

    @Slot(str, str, str, bool, bool)
    def sendCodexPracticeMessage(
        self,
        message: str,
        mode: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> None:
        try:
            preview = build_practice_context_preview(
                self.repo_root,
                self.service.catalog,
                self._profile_id,
                mode=mode,
                help_level=help_level if mode == "teacher" else None,
                include_submission=include_submission,
                include_test_output=include_test_output,
            )
            self.sendCodexMessage(
                preview.selected_text + "\n\n## Learner request\n" + message
            )
        except Exception as error:
            self._show_error(error)

    @Slot(str, bool)
    def sendCodexInterviewAnswer(
        self, answer: str, include_materials: bool = True
    ) -> None:
        if not self._interview.get("interview_id"):
            self.toast.emit("请先开始一场模拟面试。")
            return
        try:
            preview = build_role_interview_context_preview(
                self.repo_root,
                self._profile_id,
                self._interview["interview_id"],
                candidate_answer=answer,
                include_materials=include_materials,
            )
            self.sendCodexMessage(
                preview.selected_text
                + "\n\nAssess with rubric evidence, identify uncertainty, and ask at most "
                "one adaptive follow-up. Do not change Practice mastery."
            )
        except Exception as error:
            self._show_error(error)

    @Slot(str, str)
    def resolveCodexApproval(self, request_id: str, decision: str) -> None:
        if self._codex_loop is None or self._codex_backend is None:
            return
        parsed: int | str = int(request_id) if request_id.isdigit() else request_id
        asyncio.run_coroutine_threadsafe(
            self._codex_backend.resolve_approval(parsed, decision), self._codex_loop
        )

    @Slot()
    def cancelCodex(self) -> None:
        if (
            self._codex_loop
            and self._codex_backend
            and self._codex_thread_id
            and self._codex_turn_id
        ):
            asyncio.run_coroutine_threadsafe(
                self._codex_backend.interrupt(self._codex_thread_id, self._codex_turn_id),
                self._codex_loop,
            )

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value in {"system", "light", "dark"}:
            self._theme = value
            self._settings.setValue("theme", value)
            self.stateChanged.emit()

    @Slot(float)
    def setFontScale(self, value: float) -> None:
        self._font_scale = max(0.85, min(1.4, value))
        self._settings.setValue("fontScale", self._font_scale)
        self.stateChanged.emit()

    @Slot(str)
    def setCodexExecutable(self, value: str) -> None:
        candidate = QUrl(value).toLocalFile() if value.startswith("file:") else value
        path = Path(candidate).expanduser()
        resolved = discover_codex_executable(path)
        if resolved is None:
            self.toast.emit(text("error.codex_missing"))
            return
        self._codex_executable = resolved
        self._settings.setValue("codexExecutable", self._codex_executable)
        self.aiStateChanged.emit()
        self.stateChanged.emit()
        self.toast.emit("Codex 可执行文件位置已保存。")

    @Slot()
    def clearCodexExecutable(self) -> None:
        self._codex_executable = ""
        self._settings.remove("codexExecutable")
        self.aiStateChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def openDataDirectory(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.repo_root)))

    @Slot()
    def openLogDirectory(self) -> None:
        self._log_root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._log_root)))

    @Slot()
    def dismissLegacyMigration(self) -> None:
        self._legacy_migration_dismissed = True
        self.stateChanged.emit()

    @Slot()
    def migrateLegacyData(self) -> None:
        if self._legacy_data_root is None:
            return
        try:
            migrate_legacy_desktop_data(self._legacy_data_root, self.repo_root)
            self._legacy_data_root = None
            self._legacy_migration_dismissed = False
            self.refresh()
            self.toast.emit("旧版学习档案已复制并校验，原目录和本地备份均已保留。")
        except Exception as error:
            self._show_error(error)

    @Slot()
    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        if self._codex_loop and self._codex_backend:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._codex_backend.close(), self._codex_loop
                )
                future.result(timeout=4)
            except Exception:
                pass
        if self._codex_loop:
            self._codex_loop.call_soon_threadsafe(self._codex_loop.stop)
