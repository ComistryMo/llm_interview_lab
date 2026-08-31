"""Qt-facing controller that delegates all domain work to ApplicationService."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import threading
from typing import Any, Callable, Mapping
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QRunnable, QSettings, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from ..ai.codex_backend import CodexAppServerBackend, CodexEvent, discover_codex_executable
from ..ai.connections import (
    delete_connection,
    list_connections,
    save_connection,
)
from ..ai.context_builder import (
    build_practice_context_preview,
    build_role_interview_context_preview,
)
from ..ai.credentials import KeyringCredentialStore
from ..ai.interview_planner import decode_personalized_questions
from ..ai.providers import create_chat_provider
from ..ai.transcription import OpenAICompatibleTranscriber
from ..application import ApplicationError, ApplicationService
from ..coach_sessions import (
    CoachSessionError,
    load_coach_sessions,
    message as coach_message,
    new_coach_session,
    write_coach_sessions,
)
from ..lifecycle import ReviewInput
from ..roles import RoleCatalogError
from ..workspace import (
    WorkspaceError,
    profile_id_for_display_name,
    profile_paths,
    load_profile,
    validate_profile_id,
)
from .i18n import friendly_error, localize_role, onboarding_error_text, text
from .runtime import is_packaged_desktop, migrate_legacy_desktop_data
from .voice import InterviewVoiceRecorder


class WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(object)


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


class StreamingWorker(QRunnable):
    """Run one cancellable provider collection without touching Qt objects.

    ``progress`` is delivered through a Qt signal, so the Controller can
    persist partial assistant output on the GUI thread.  The operation gets a
    callback and a cancellation event; providers that support native
    cancellation can observe it between chunks, while slower adapters still
    resolve to a truthful stopped state when the next chunk arrives.
    """

    def __init__(
        self,
        operation: Callable[[Callable[[str], None], threading.Event], Any],
    ) -> None:
        super().__init__()
        self.operation = operation
        self.cancel_event = threading.Event()
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self.operation(self.signals.progress.emit, self.cancel_event)
            self.signals.completed.emit(result)
        except Exception as error:  # UI boundary: provider errors are sanitized later.
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


def _codex_terminal_outcome(params: Mapping[str, Any]) -> tuple[str, str]:
    """Normalize App Server terminal metadata without treating failure as success.

    Some App Server versions report an interrupted/failed turn through the
    ``turn/completed`` notification and put the actual status under a nested
    ``turn`` object. Older adapters omit the field entirely, in which case
    the notification itself is the only success signal. Unknown explicit
    statuses fail closed so the UI never labels an unverified response as a
    completed answer or scorecard.
    """

    nested = params.get("turn")
    turn = nested if isinstance(nested, Mapping) else {}
    raw_status = turn.get("status") or params.get("status")
    raw_error = turn.get("error") or params.get("error") or params.get("message")
    if isinstance(raw_error, Mapping):
        raw_error = (
            raw_error.get("message")
            or raw_error.get("detail")
            or raw_error.get("code")
            or ""
        )
    status = str(raw_status or "").strip().lower()
    detail = str(raw_error or "").strip()
    success_statuses = {"completed", "complete", "success", "succeeded"}
    if status in {"interrupted", "aborted", "cancelled", "canceled"}:
        return "cancelled", detail or "Codex 回答已停止，未生成完整结果。"
    if status in {"failed", "error", "errored"}:
        return "error", detail or "Codex 回答失败，请检查连接后重试。"
    if detail and status not in success_statuses:
        return "error", detail
    if status and status not in success_statuses:
        return "error", f"Codex 返回未完成状态（{status}），请重试。"
    return "completed", ""


def _demo_dashboard() -> dict[str, Any]:
    return {
        "profile_id": "demo",
        "role": {
            "primary_role": "applied_ai_engineer",
            "title": "Applied AI Engineer",
            "seniority": "new_grad",
            "ai_mode": "disabled",
        },
        "current": {
            "problem_id": "LOSS-014",
            "title": "Cross Entropy",
            "status": "in_progress",
            "environment": "当前可运行",
            "environment_available": True,
        },
        "recommended_quests": [
            {"id": "tensor_stable_loss", "title": "Tensor & Stable Loss"},
            {"id": "optimizer_training", "title": "Optimizer & Training Loop"},
        ],
        "due_review": ["TNS-011"],
        "due_retention": [{"problem_id": "LOSS-007", "stage": "d7", "due_at": "2026-08-28"}],
        "unlocks": [
            {
                "problem_id": "OPT-001",
                "title": "SGD",
                "environment": "当前可运行",
                "environment_available": True,
            }
        ],
        "mastered_count": 14,
        "role_readiness_metric_version": 2,
        "role_readiness": [
            {
                "id": "python_engineering", "label": "Python 工程",
                "assessed_mastery": 0.75, "assessment_coverage": 0.62,
                "assessment_coverage_ceiling": 0.88,
                "self_assessed_attainment": 0.75, "self_assessment_coverage": 1.0,
                "assessed_problem_count": 5, "assessable_problem_count": 8,
                "mastered_problem_count": 4, "evidence_scope": "practice",
                "self_reported": 0.75, "verified": 0.75,
            },
            {
                "id": "deep_learning", "label": "深度学习",
                "assessed_mastery": 0.60, "assessment_coverage": 0.48,
                "assessment_coverage_ceiling": 0.78,
                "self_assessed_attainment": 0.65, "self_assessment_coverage": 1.0,
                "assessed_problem_count": 4, "assessable_problem_count": 7,
                "mastered_problem_count": 2, "evidence_scope": "practice",
                "self_reported": 0.65, "verified": 0.60,
            },
            {
                "id": "llm_vlm", "label": "LLM / VLM",
                "assessed_mastery": 0.50, "assessment_coverage": 0.36,
                "assessment_coverage_ceiling": 0.70,
                "self_assessed_attainment": 0.55, "self_assessment_coverage": 1.0,
                "assessed_problem_count": 3, "assessable_problem_count": 8,
                "mastered_problem_count": 2, "evidence_scope": "practice",
                "self_reported": 0.55, "verified": 0.50,
            },
            {
                "id": "system_design", "label": "系统设计",
                "assessed_mastery": None, "assessment_coverage": 0.0,
                "assessment_coverage_ceiling": 0.20,
                "self_assessed_attainment": 0.45, "self_assessment_coverage": 1.0,
                "assessed_problem_count": 0, "assessable_problem_count": 1,
                "mastered_problem_count": 0, "evidence_scope": "practice",
                "self_reported": 0.45, "verified": 0.0,
            },
        ],
    }


class AppController(QObject):
    stateChanged = Signal()
    busyChanged = Signal()
    pageChanged = Signal()
    toast = Signal(str)
    aiDelta = Signal(str)
    # Scoped stream event for QML/other clients.  ``aiDelta`` remains for
    # legacy consumers, while this payload prevents a late turn from being
    # mistaken for the currently selected session.
    coachDelta = Signal("QVariantMap")
    # Codex reads events on its dedicated asyncio thread.  Emitting this
    # signal and handling it on the QObject's thread keeps QML-visible state
    # mutations serialized with user actions.
    _codexEventReceived = Signal(object)
    _codexPumpEnded = Signal(object)
    _codexConnectReady = Signal(object)
    _codexConnectFailed = Signal(object)
    _codexTurnStarted = Signal(object)
    _codexApprovalResult = Signal(object)
    aiStateChanged = Signal()
    interviewPlanReady = Signal()
    interviewTranscriptReady = Signal(str)
    codexApproval = Signal("QVariantMap")
    codexApprovalResolved = Signal(str)
    codexApprovalFailed = Signal("QVariantMap")
    # Coach state is intentionally exposed as a few thin properties rather
    # than a second global store.  Every mutation remains scoped to the
    # currently selected Profile and is persisted under that Profile.
    coachChanged = Signal()
    coachStreamingChanged = Signal()
    coachErrorChanged = Signal()

    def __init__(
        self,
        repo_root: Path,
        *,
        profile_id: str = "default",
        demo_page: str | None = None,
        demo_theme: str | None = None,
        service: ApplicationService | None = None,
        legacy_data_root: Path | None = None,
        log_root: Path | None = None,
    ) -> None:
        super().__init__()
        self.repo_root = repo_root.resolve()
        self.service = service or ApplicationService(self.repo_root)
        self._demo_mode = demo_page is not None
        requested_profile_id = str(profile_id or "default").strip() or "default"
        self._profile_id = requested_profile_id
        self._profile_display_name = profile_id
        self._page = demo_page or "home"
        self._onboarding = False
        self._onboarding_busy = False
        self._onboarding_error = ""
        self._onboarding_error_code = ""
        self._onboarding_result: dict[str, Any] = {
            "success": False,
            "error_code": "",
            "user_message": "",
            "technical_message": "",
            "recommended_action": "",
            "operation_id": "",
        }
        self._dashboard: dict[str, Any] = {}
        self._problems: list[dict[str, Any]] = []
        self._current_task: dict[str, Any] = {}
        self._submission = ""
        self._submission_saved_revision = ""
        self._tested_revision = ""
        self._test_state = "未测试"
        self._test_operation_id = ""
        self._test_identity: tuple[str, str, str] | None = None
        self._test_output = ""
        self._interview: dict[str, Any] = {}
        self._interview_plan_preview: dict[str, Any] = {}
        self._interview_plan_request: dict[str, Any] | None = None
        self._voice_recorder = InterviewVoiceRecorder(self)
        self._voice_transcription_state = "idle"
        self._voice_transcription_error = ""
        self._voice_transcription_operation_id = ""
        self._voice_question_key = ""
        self._voice_recorder.changed.connect(self._voice_state_changed)
        self._voice_recorder.failed.connect(self._voice_failed)
        self._recent_interview: dict[str, Any] = {}
        self._connections: list[dict[str, Any]] = []
        self._connection_error = ""
        self._materials: list[dict[str, Any]] = []
        # The interview knowledge bundle is a read-only, lazy-loaded UI
        # surface.  Keep it separate from Practice problems and Profile
        # events so opening/searching the browser cannot affect mastery.
        self._knowledge_cards: list[dict[str, Any]] = []
        self._knowledge_detail: dict[str, Any] = {}
        self._knowledge_loaded = False
        self._pending_ai_assessment: dict[str, Any] | None = None
        self._coach_sessions: list[dict[str, Any]] = []
        self._active_coach_session_id = ""
        self._coach_messages: list[dict[str, Any]] = []
        self._coach_streaming = False
        self._coach_error = ""
        self._coach_operation_id = ""
        self._coach_message_id = ""
        self._coach_worker: StreamingWorker | None = None
        self._coach_identity: tuple[str, str, str, str, str] | None = None
        self._coach_cancel_event: threading.Event | None = None
        self._busy = False
        # Track each background operation independently.  A fast connection
        # probe must not clear the busy state while a test or interview grader
        # is still running.
        self._background_operations: set[str] = set()
        self._background_generation = 0
        self._ai_status = text("status.ai_offline")
        self._workers: set[Worker] = set()
        self._thread_pool = QThreadPool.globalInstance()
        self._settings = QSettings("ComistryMo", "LLMInterviewLab")
        # A packaged desktop launch has no CLI argument with which to recover
        # the last Profile.  Store only the safe internal id, scoped to this
        # repository/data root, so a different checkout can never select a
        # Profile merely because it used the same Qt settings namespace.
        self._active_profile_key = self._active_profile_settings_key()
        if not self._demo_mode:
            self._profile_id = self._restore_active_profile_id(requested_profile_id)
        self._theme = str(self._settings.value("theme", "system"))
        self._font_scale = float(self._settings.value("fontScale", 1.0))
        if demo_page:
            # Release screenshots and offscreen smoke evidence must not inherit
            # a maintainer's persisted theme or accessibility settings.
            self._theme = demo_theme if demo_theme in {"light", "dark", "system"} else "light"
            self._font_scale = 1.0
        # A demo/screenshot controller is deliberately hermetic.  Do not read
        # or mutate a maintainer's persisted Codex path: Settings.qml is still
        # rendered for visual coverage, but it must never expose local machine
        # configuration in synthetic evidence.
        self._codex_executable = "" if demo_page else str(
            self._settings.value("codexExecutable", "")
        )
        self._codex_available = False
        self._codex_probe_running = False
        self._legacy_data_root = (
            None
            if self._demo_mode
            else legacy_data_root.resolve() if legacy_data_root else None
        )
        self._legacy_migration_dismissed = False
        self._log_root = (log_root or (self.repo_root / "logs")).resolve()
        self._codex_loop: asyncio.AbstractEventLoop | None = None
        self._codex_thread: threading.Thread | None = None
        self._codex_backend: CodexAppServerBackend | None = None
        self._codex_thread_id: str | None = None
        # One App Server process may host several isolated threads.  Keep the
        # workflow mode alongside each id so a repository-agent (write)
        # thread can never be reused by Coach/Interview (read-only).
        self._codex_threads: dict[str, str] = {}
        self._codex_thread_mode: str | None = None
        self._codex_turn_id: str | None = None
        self._codex_coach_identity: tuple[str, str, str, str, str] | None = None
        self._codex_coach_turn_id: str | None = None
        self._codex_interview_identity: tuple[str, str, str, str, str] | None = None
        self._codex_interview_turn_id: str | None = None
        self._codex_interview_buffer = ""
        self._codex_interview_dimensions: set[str] = set()
        self._codex_interview_fatal_issues: set[str] = set()
        self._codex_interview_operation_id = ""
        self._codex_interview_message_id = ""
        self._interview_provider_operation_id = ""
        self._codex_connect_future: Any | None = None
        self._codex_connect_generation = 0
        self._codex_active_connect_token = ""
        self._codex_pump_started = False
        self._codex_drain_pending = False
        self._codex_drain_turn_id: str | None = None
        # App Server events are delivered over one shared stream.  These
        # guards make an event belong to the currently-started request before
        # it can mutate either Coach or Interview state.  In particular, an
        # id-less event is never accepted after a concrete turn id has been
        # observed (or after a previous turn completed).
        self._codex_turn_generation = 0
        self._codex_active_generation = 0
        self._codex_turn_started = False
        self._codex_start_ready = False
        self._codex_start_response_turn_id = ""
        self._codex_unscoped_allowed = False
        # The event pump and the ``turn/start`` response are delivered through
        # separate queued signals. A concrete ``turn/started``/delta/terminal
        # event can therefore reach the Controller a few moments before the
        # response callback binds its id. Keep only those bounded, explicitly
        # identified events until the callback can prove the id belongs to the
        # current operation; id-less events are discarded fail-closed.
        self._codex_early_events: list[CodexEvent] = []
        self._codex_cancel_pending_operation = ""
        self._codex_cancel_pending_kind = ""
        self._codex_drain_waiting_start = False
        self._codex_drain_token = ""
        self._codex_backend_generation = 0
        self._codex_pending_approval: dict[str, Any] | None = None
        self._interview_coding_identity: tuple[str, str, str, str, str] | None = None
        self._interview_coding_tested_revision = ""
        self._interview_coding_test_operation_id = ""
        self._codex_diff = ""
        self._shutdown_done = False
        self._codexEventReceived.connect(self._handle_codex_event)
        self._codexPumpEnded.connect(self._handle_codex_pump_ended)
        self._codexConnectReady.connect(self._handle_codex_connect_ready)
        self._codexConnectFailed.connect(self._handle_codex_connect_failed)
        self._codexTurnStarted.connect(self._handle_codex_turn_started)
        self._codexApprovalResult.connect(self._handle_codex_approval_result)
        if demo_page:
            self._load_demo(demo_page)
        else:
            self.refresh()
            # Finder/Explorer startup must not synchronously scan PATH or
            # launch a subprocess from a QML property getter.
            QTimer.singleShot(0, self.refreshCodexAvailability)

    def _load_demo(self, page: str) -> None:
        self._profile_id = "demo"
        self._profile_display_name = "演示学习档案"
        self._onboarding = page == "onboarding"
        self._dashboard = _demo_dashboard()
        self._problems = [
            {"problem_id": "TNS-011", "title": "Last Valid Token", "status": "mastered", "asset_status": "ready", "validation": "oracle", "locked": False, "retention": True, "skills": ["Tensor indexing"], "environment": "当前可运行", "environment_available": True, "recommendable": True, "recommended_rank": 0},
            {"problem_id": "LOSS-014", "title": "Cross Entropy", "status": "in_progress", "asset_status": "ready", "validation": "oracle", "locked": False, "retention": True, "skills": ["Loss", "数值稳定"], "environment": "当前可运行", "environment_available": True, "recommendable": True, "recommended_rank": 1},
            {"problem_id": "ATT-002", "title": "Scaled Dot-Product Attention", "status": "not_started", "asset_status": "ready", "validation": "oracle", "locked": True, "retention": False, "skills": ["Attention"], "environment": "需要 PyTorch 练习环境", "environment_available": False, "recommendable": True, "recommended_rank": 2},
        ]
        self._current_task = {
            "problem_id": "LOSS-014",
            "title": "Cross Entropy",
            "task": "Implement numerically stable cross entropy for batched logits.\n\nInput shape: logits [B, C], targets [B].",
            "environment": "当前可运行",
            "environment_available": True,
            "actions": {
                "review": {"state": "blocked", "actionable": False, "blocked_reason": "先完成实现。"},
                "retention": {
                    "d2": {"state": "future", "actionable": False, "blocked_reason": "尚未到期。"},
                    "d7": {"state": "blocked", "actionable": False, "blocked_reason": "先通过 D+2。"},
                },
            },
        }
        self._submission = "def cross_entropy(logits, targets):\n    # Your implementation\n    raise NotImplementedError\n"
        self._submission_saved_revision = hashlib.sha256(self._submission.encode()).hexdigest()
        self._tested_revision = ""
        self._test_state = "未测试"
        self._test_output = "尚未运行公开测试。"
        self._interview = {
            "interview_id": "role-interview-demo",
            "status": "active",
            "role_id": "applied_ai_engineer",
            "role_title": "应用型 AI 工程师",
            "seniority": "new_grad",
            "difficulty": "medium",
            "blueprint_id": "interview.applied_ai_engineer.new_grad",
            "ai_mode": "provider",
            "material_refs": [],
            "remaining_seconds": 3120,
            "resume_available": True,
            "expired": False,
            "completed_questions": 3,
            "total_questions": 6,
            "question": {
                "question_id": "q-002",
                "kind": "system_design",
                "title": "设计可靠的工具调用助手",
                "prompt": "请设计一个生产级工具调用助手：说明参数校验、工具执行、重试与超时、可观测性，以及工具失败时的降级和人工接管方案。",
                "rubric": {"dimensions": {"failure_handling": {}, "tradeoffs": {}, "evaluation": {}}},
            },
        }
        self._recent_interview = {
            "interview_id": "role-interview-demo-previous",
            "status": "incomplete",
            "completion_status": "incomplete",
            "overall_score": 68.0,
            "finished_at": "2026-08-29T16:40:00+00:00",
            "summary": "示例面试已留档；评分只基于已记录证据。",
        }
        self._connections = [
            {"connection_id": "ollama-local", "provider_id": "ollama", "display_name": "本地 Ollama", "model": "qwen", "status": "尚未测试", "ready": False},
        ]
        self._materials = [
            {
                "id": "resume-demo",
                "kind": "resume",
                "title": "示例候选人简历",
                "sha256": "4" * 64,
                "size_bytes": 512,
                "relative_path": "materials/files/resume-demo.md",
                "tags": ["synthetic"],
                "ai_access": True,
            }
        ]
        # Demo/screenshot state is synthetic and read-only.  It mirrors the
        # persisted shape so the Coach page can be reviewed without opening a
        # real Profile or contacting a provider.
        self._coach_sessions = [
            {
                "session_id": "coach-deadbeef000000",
                "profile_id": "demo",
                "title": "Cross Entropy · 复盘",
                "mode": "coach",
                "provider_kind": "none",
                "provider_id": "none",
                "model": "",
                "problem_id": "LOSS-014",
                "status": "idle",
                "created_at": "2026-08-30T08:00:00+00:00",
                "updated_at": "2026-08-30T08:16:00+00:00",
                "draft": "",
                "context": {
                    "references": ["policy", "task", "test"],
                    "hashes": {"policy": "a" * 64, "task": "b" * 64, "test": "c" * 64},
                },
                "messages": [
                    {
                        "message_id": "msg-deadbeef000000",
                        "role": "user",
                        "content": "先帮我确认数值稳定性的检查顺序。",
                        "created_at": "2026-08-30T08:15:00+00:00",
                        "metadata": {"provider_kind": "demo"},
                    },
                    {
                        "message_id": "msg-deadbeef000001",
                        "role": "assistant",
                        "content": "先核对输入 shape 与 dtype，再检查 log-sum-exp 的减最大值步骤；公开测试只说明行为，不等于掌握。",
                        "created_at": "2026-08-30T08:16:00+00:00",
                        "metadata": {"provider_kind": "demo"},
                    },
                ],
                "last_turn": None,
            }
        ]
        self._active_coach_session_id = self._coach_sessions[0]["session_id"]
        self._coach_messages = list(self._coach_sessions[0]["messages"])
        self._coach_error = ""
        # Demo pages remain deterministic and do not need to parse the real
        # bundle until the user explicitly opens the knowledge browser.
        self._knowledge_cards = []
        self._knowledge_detail = {}
        self._knowledge_loaded = False
        self._localize_dashboard()

    @Property(str, notify=stateChanged)
    def profileId(self) -> str:
        return self._profile_id

    @Property(str, notify=stateChanged)
    def activeProfileId(self) -> str:
        """The Profile selected for this desktop process.

        This is deliberately an alias of the controller's explicit Profile,
        not a second state source.  It is useful to the shell when explaining
        which local data will be opened after a restart.
        """

        return self._profile_id

    @Property(str, notify=stateChanged)
    def profileDisplayName(self) -> str:
        return self._profile_display_name

    @Property(bool, notify=stateChanged)
    def onboardingRequired(self) -> bool:
        return self._onboarding

    @Property(bool, notify=stateChanged)
    def onboardingBusy(self) -> bool:
        return self._onboarding_busy

    @Property(str, notify=stateChanged)
    def onboardingError(self) -> str:
        return self._onboarding_error

    @Property(str, notify=stateChanged)
    def onboardingErrorCode(self) -> str:
        return self._onboarding_error_code

    @Property("QVariantMap", notify=stateChanged)
    def onboardingResult(self) -> dict[str, Any]:
        return self._onboarding_result

    @Property("QVariantList", notify=stateChanged)
    def roles(self) -> list[dict[str, Any]]:
        return [localize_role(card) for card in self.service.role_cards()]

    @Slot(str, str, str, result="QVariantMap")
    def interviewConfiguration(
        self, role_id: str, seniority: str, difficulty: str
    ) -> dict[str, Any]:
        return self.service.interview_configuration(role_id, seniority, difficulty)

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
    def submissionRevision(self) -> str:
        return hashlib.sha256(self._submission.encode("utf-8")).hexdigest()

    @Property(str, notify=stateChanged)
    def testedRevision(self) -> str:
        return self._tested_revision

    @Property(str, notify=stateChanged)
    def testState(self) -> str:
        return self._test_state

    @Property(str, notify=stateChanged)
    def testOperationId(self) -> str:
        return self._test_operation_id

    @Property(bool, notify=stateChanged)
    def submissionDirty(self) -> bool:
        return bool(self._submission_saved_revision) and (
            self.submissionRevision != self._submission_saved_revision
        )

    @Property(str, notify=stateChanged)
    def testOutput(self) -> str:
        return self._test_output

    @Property("QVariantMap", notify=stateChanged)
    def interview(self) -> dict[str, Any]:
        return self._interview

    @Property("QVariantMap", notify=stateChanged)
    def interviewPlanPreview(self) -> dict[str, Any]:
        """The no-write AI plan awaiting explicit user confirmation."""

        return dict(self._interview_plan_preview)

    @Property("QVariantMap", notify=stateChanged)
    def interviewVoice(self) -> dict[str, Any]:
        return {
            "state": self._voice_recorder.state,
            "duration_ms": self._voice_recorder.duration_ms,
            "audio_ready": self._voice_recorder.state == "recorded",
            "error": self._voice_recorder.error_message
            or self._voice_transcription_error,
            "transcription_state": self._voice_transcription_state,
        }

    @Property("QVariantMap", notify=stateChanged)
    def recentInterview(self) -> dict[str, Any]:
        """A compact current-Profile result summary for the Home page."""

        return dict(self._recent_interview)

    @Property("QVariantList", notify=stateChanged)
    def connections(self) -> list[dict[str, Any]]:
        return self._connections

    @Property(str, notify=stateChanged)
    def connectionError(self) -> str:
        """Last actionable connection error for the Connections page."""

        return self._connection_error

    @Property("QVariantList", constant=True)
    def providerOptions(self) -> list[str]:
        """Expose only adapters shipped by the current distribution."""

        if is_packaged_desktop():
            return ["openai", "openai-compatible", "ollama"]
        return ["openai", "openai-compatible", "ollama", "anthropic", "gemini"]

    @Property("QVariantList", notify=stateChanged)
    def materials(self) -> list[dict[str, Any]]:
        return self._materials

    @Property("QVariantList", notify=coachChanged)
    def coachSessions(self) -> list[dict[str, Any]]:
        """Return lightweight summaries for the session switcher.

        Message bodies stay in ``coachMessages`` for the selected session so a
        sidebar cannot accidentally render or transmit another conversation.
        """

        return [
            {
                "session_id": item["session_id"],
                "profile_id": item["profile_id"],
                "title": item["title"],
                "mode": item["mode"],
                "provider_kind": item.get("provider_kind", "none"),
                "provider_id": item.get("provider_id", ""),
                "model": item.get("model", ""),
                "problem_id": item.get("problem_id"),
                "status": item.get("status", "idle"),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "message_count": len(item.get("messages", [])),
                "draft": item.get("draft", ""),
            }
            for item in self._coach_sessions
        ]

    @Property("QVariantMap", notify=coachChanged)
    def activeCoachSession(self) -> dict[str, Any]:
        for item in self._coach_sessions:
            if item.get("session_id") == self._active_coach_session_id:
                return {
                    **item,
                    # QML only needs the selected transcript through the
                    # dedicated property; avoid duplicating large bodies here.
                    "messages": [],
                }
        return {}

    @Property("QVariantList", notify=coachChanged)
    def coachMessages(self) -> list[dict[str, Any]]:
        return list(self._coach_messages)

    @Property(bool, notify=coachStreamingChanged)
    def coachStreaming(self) -> bool:
        return self._coach_streaming

    @Property(str, notify=coachErrorChanged)
    def coachError(self) -> str:
        return self._coach_error

    @Property(str, notify=coachChanged)
    def coachOperationId(self) -> str:
        return self._coach_operation_id

    @Property(str, notify=coachChanged)
    def coachMessageId(self) -> str:
        return self._coach_message_id
    @Property("QVariantList", notify=stateChanged)
    def knowledgeCards(self) -> list[dict[str, Any]]:
        """Compact, answer-free cards shown by the optional UI browser."""

        return self._knowledge_cards

    @Property("QVariantMap", notify=stateChanged)
    def knowledgeDetail(self) -> dict[str, Any]:
        """Currently selected full card, including resolved source records."""

        return self._knowledge_detail

    @Property(bool, notify=stateChanged)
    def knowledgeLoaded(self) -> bool:
        return self._knowledge_loaded

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

    @Property(str, notify=aiStateChanged)
    def aiStatusVariant(self) -> str:
        """Return a localization-independent presentation state for the shell."""

        if (
            self._codex_connect_future is not None
            and not self._codex_connect_future.done()
        ):
            return "connecting"
        if self._codex_backend is not None and self._codex_thread_id:
            return "connected"
        return "offline"

    @Property(bool, notify=aiStateChanged)
    def codexAvailable(self) -> bool:
        return self._codex_available

    @Property(str, notify=stateChanged)
    def dataDirectory(self) -> str:
        return "<synthetic-workspace>" if self._demo_mode else str(self.repo_root)

    @Property(str, notify=stateChanged)
    def logDirectory(self) -> str:
        return "<synthetic-log-directory>" if self._demo_mode else str(self._log_root)

    @Property(str, notify=stateChanged)
    def codexExecutable(self) -> str:
        return self._codex_executable

    @Property(bool, notify=stateChanged)
    def legacyMigrationAvailable(self) -> bool:
        return (
            not self._demo_mode
            and self._legacy_data_root is not None
            and not self._legacy_migration_dismissed
        )

    @Property(str, notify=stateChanged)
    def legacyDataDirectory(self) -> str:
        return "" if self._demo_mode or self._legacy_data_root is None else str(self._legacy_data_root)

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        return text(key)

    def _show_error(self, error: BaseException | str) -> None:
        self.toast.emit(friendly_error(error))

    def _onboarding_failure(
        self, code: str, stage: str, error: BaseException | None = None
    ) -> bool:
        self._onboarding_error_code = code
        self._onboarding_error = onboarding_error_text(code)
        error_type = type(error).__name__ if error is not None else "InputError"
        detail = ""
        if error is not None:
            detail = " ".join(str(error).split())
            for private_path in (str(self.repo_root), str(Path.home())):
                if private_path:
                    detail = detail.replace(private_path, "<local-path>")
            detail = detail[:400]
        logging.getLogger("llm_interview_lab.desktop").error(
            "onboarding_failed code=%s stage=%s error_type=%s detail=%s",
            code,
            stage,
            error_type,
            detail,
        )
        self._onboarding_result = {
            "success": False,
            "error_code": code,
            "user_message": self._onboarding_error,
            "technical_message": detail,
            "recommended_action": "请按提示修正后重试；如仍失败，请打开本地日志。",
            "operation_id": self._onboarding_result.get("operation_id") or uuid4().hex,
            "stage": stage,
        }
        self.stateChanged.emit()
        return False

    @Slot()
    def clearOnboardingError(self) -> None:
        if self._onboarding_error or self._onboarding_error_code:
            self._onboarding_error = ""
            self._onboarding_error_code = ""
            self._onboarding_result = {
                "success": False,
                "error_code": "",
                "user_message": "",
                "technical_message": "",
                "recommended_action": "",
                "operation_id": "",
            }
            self.stateChanged.emit()

    def _localize_dashboard(self) -> None:
        role = self._dashboard.get("role")
        if isinstance(role, dict) and role.get("primary_role"):
            localized = localize_role({"id": role["primary_role"]})
            role["title"] = localized.get("title", role.get("title", ""))

    def _cancel_coach_stream_for_reload(self) -> None:
        """Invalidate an in-flight Coach turn before replacing Profile state.

        Refresh can be triggered by connection/material changes while a
        provider worker is still producing chunks.  Marking the transcript
        stopped and clearing every identity component makes late callbacks
        harmless and avoids a permanently busy page after a profile reload.
        """

        identity = self._coach_identity
        interview_operation = self._codex_interview_operation_id
        if self._coach_worker is not None:
            self._coach_worker.cancel_event.set()
        if identity is not None:
            session = self._coach_session(identity[1])
            if session is not None:
                session["status"] = "stopped"
                session["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                if self._profile_id != "demo":
                    try:
                        self._persist_coach_sessions()
                    except Exception:
                        pass
        if identity is not None and identity[4] == "codex":
            # Native interrupt is best effort; identity invalidation below is
            # the correctness boundary when the backend is unavailable.
            self._codex_drain_pending = True
            self._codex_drain_turn_id = self._codex_coach_turn_id
            self._codex_drain_waiting_start = bool(
                self._codex_coach_turn_id
                and str(self._codex_coach_turn_id).startswith("pending:")
            )
            self._codex_cancel_pending_operation = (
                identity[2] if self._codex_drain_waiting_start else ""
            )
            self._codex_cancel_pending_kind = "coach" if self._codex_drain_waiting_start else ""
            self._codex_drain_token = uuid4().hex
            self._schedule_codex_drain_timeout(self._codex_drain_token)
            # A pending sentinel is local-only and must never be sent to the
            # App Server.  The queued start callback will bind and interrupt
            # the concrete server id for this exact operation.
            if (
                self._codex_coach_turn_id
                and not str(self._codex_coach_turn_id).startswith("pending:")
            ):
                self._interrupt_codex_turn(str(self._codex_coach_turn_id))
        if self._codex_interview_identity is not None:
            self._codex_drain_pending = True
            self._codex_drain_turn_id = self._codex_interview_turn_id
            self._codex_drain_waiting_start = bool(
                self._codex_interview_turn_id
                and str(self._codex_interview_turn_id).startswith("pending:")
            )
            self._codex_cancel_pending_operation = (
                self._codex_interview_identity[3]
                if self._codex_drain_waiting_start
                else ""
            )
            self._codex_cancel_pending_kind = (
                "interview" if self._codex_drain_waiting_start else ""
            )
            self._codex_drain_token = uuid4().hex
            self._schedule_codex_drain_timeout(self._codex_drain_token)
            if (
                self._codex_interview_turn_id
                and not str(self._codex_interview_turn_id).startswith("pending:")
            ):
                self._interrupt_codex_turn(str(self._codex_interview_turn_id))
        if interview_operation:
            self._background_operations.discard(interview_operation)
            self._set_busy(bool(self._background_operations))
        self._codex_interview_identity = None
        self._codex_interview_turn_id = None
        self._codex_interview_buffer = ""
        self._codex_interview_dimensions = set()
        self._codex_interview_fatal_issues = set()
        self._codex_interview_operation_id = ""
        self._codex_interview_message_id = ""
        self._interview_provider_operation_id = ""
        self._coach_identity = None
        self._codex_coach_identity = None
        self._codex_coach_turn_id = None
        self._coach_worker = None
        self._coach_cancel_event = None
        self._coach_operation_id = ""
        self._coach_message_id = ""
        self._finish_codex_event_gate()
        self._set_coach_streaming(False)

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    def _voice_state_changed(self) -> None:
        self.stateChanged.emit()

    def _voice_failed(self, message: str) -> None:
        self._voice_transcription_error = friendly_error(message)
        self.stateChanged.emit()

    def _active_profile_settings_key(self) -> str:
        """Return a stable, non-sensitive QSettings key for this data root."""

        root_digest = hashlib.sha256(
            str(self.repo_root).encode("utf-8", errors="replace")
        ).hexdigest()[:16]
        return f"profiles/{root_digest}/active_profile_id"

    def _restore_active_profile_id(self, requested: str) -> str:
        """Recover the last explicitly opened Profile without enumeration.

        ``default`` is the only implicit request.  Explicit CLI/profile
        selections always win, which keeps the public CLI deterministic and
        prevents a stale desktop preference from opening another Profile.
        """

        if requested != "default":
            return requested
        candidate = str(self._settings.value(self._active_profile_key, "") or "").strip()
        if not candidate:
            return requested
        try:
            validate_profile_id(candidate)
            path = profile_paths(self.repo_root, candidate).profile_file
        except (TypeError, ValueError, WorkspaceError):
            return requested
        return candidate if path.is_file() else requested

    def _persist_active_profile_id(self) -> None:
        """Remember the current safe Profile for the next desktop launch."""

        if self._demo_mode or not self._profile_id:
            return
        try:
            validate_profile_id(self._profile_id)
            self._settings.setValue(self._active_profile_key, self._profile_id)
            # ``sync`` is intentionally limited to this small preference;
            # Profile facts and learning events remain Workspace sources of
            # truth and are never mirrored into QSettings.
            self._settings.sync()
        except (TypeError, ValueError, WorkspaceError):
            # A preference failure must not block local training.  The next
            # launch will simply fall back to the requested/default Profile.
            logging.getLogger("llm_interview_lab.desktop").warning(
                "active_profile_preference_unavailable error_type=preference"
            )

    def _load_profile_state(self) -> None:
        self._cancel_coach_stream_for_reload()
        paths = profile_paths(self.repo_root, self._profile_id)
        profile = load_profile(paths, self.repo_root)
        self._profile_display_name = profile.get("display_name", self._profile_id)
        self._dashboard = self.service.dashboard(self._profile_id)
        self._localize_dashboard()
        self._problems = self.service.problem_cards(self._profile_id)
        self._submission = ""
        self._submission_saved_revision = ""
        self._tested_revision = ""
        self._test_state = "未测试"
        self._test_operation_id = ""
        self._test_identity = None
        self._interview_coding_identity = None
        self._interview_coding_tested_revision = ""
        self._interview_coding_test_operation_id = ""
        self._current_task = {}
        current = self.service.current_submission(self._profile_id)
        if current:
            self._current_task = self.service.problem_view(current["problem_id"])
            self._current_task["actions"] = self.service.practice_actions(
                self._profile_id, current["problem_id"]
            )
            self._submission = current["text"]
            self._submission_saved_revision = current["sha256"]
            last_test = current.get("last_public_test") or {}
            if (
                last_test.get("status") == "passed"
                and last_test.get("submission_sha256") == current["sha256"]
            ):
                self._tested_revision = current["sha256"]
                self._test_state = "测试通过"
            else:
                self._tested_revision = ""
                self._test_state = "未测试"
            self._test_operation_id = ""
            self._test_identity = (
                current["problem_id"], current["attempt_id"], self._profile_id
            )
        self._connections = [
            {**config.__dict__, "status": "已保存，尚未测试", "ready": False}
            for config in list_connections(self.repo_root, self._profile_id)
        ]
        self._connection_error = ""
        self._materials = self.service.material_cards(self._profile_id)
        self._load_coach_state()
        self._interview = {}
        self._recent_interview = {}
        # A Profile without a resumable interview must not inherit audio or
        # transcription state from the Profile that was open before it. The
        # identity fence in ``_load_interview`` handles active sessions; this
        # reset covers the no-session branch as well.
        self._voice_recorder.reset()
        self._voice_transcription_state = "idle"
        self._voice_transcription_error = ""
        self._voice_transcription_operation_id = ""
        self._voice_question_key = f"{self._profile_id}::"
        try:
            preferred = self.service.preferred_interview(self._profile_id)
            if preferred is not None:
                self._load_interview(preferred["interview_id"])
            recent = self.service.recent_interview_result(self._profile_id)
            if isinstance(recent, Mapping):
                self._recent_interview = {
                    key: recent.get(key)
                    for key in (
                        "interview_id",
                        "status",
                        "completion_status",
                        "overall_score",
                        "finished_at",
                        "summary",
                    )
                    if recent.get(key) is not None
                }
        except Exception as error:
            logging.getLogger("llm_interview_lab.desktop").warning(
                "interview_resume_unavailable error_type=%s",
                type(error).__name__,
            )
        self._onboarding = False
        self._persist_active_profile_id()

    def _load_coach_state(self) -> None:
        """Load only the selected Profile's resumable Coach conversations."""

        try:
            self._coach_sessions = load_coach_sessions(self.repo_root, self._profile_id)
            # A persisted ``streaming`` marker only means the previous process
            # stopped before receiving a terminal callback.  No worker exists
            # after restart, so expose a recoverable stopped state instead of
            # a spinner that can neither Stop nor Retry.
            recovered_stream = False
            for session in self._coach_sessions:
                if session.get("status") == "streaming":
                    session["status"] = "stopped"
                    recovered_stream = True
            if recovered_stream:
                self._coach_sessions = write_coach_sessions(
                    self.repo_root, self._profile_id, self._coach_sessions
                )
            if self._active_coach_session_id not in {
                item["session_id"] for item in self._coach_sessions
            }:
                self._active_coach_session_id = (
                    self._coach_sessions[0]["session_id"] if self._coach_sessions else ""
                )
            self._sync_active_coach_messages()
            self._coach_error = ""
        except (CoachSessionError, WorkspaceError, OSError) as error:
            # A damaged transcript must not prevent Practice/Interview from
            # opening.  Keep it isolated to this Profile and surface a
            # recoverable message in the Coach page.
            self._coach_sessions = []
            self._active_coach_session_id = ""
            self._coach_messages = []
            self._coach_error = (
                "本地 Coach 会话无法读取；未修改原文件。请在设置中打开数据目录，"
                "备份后修复或删除该会话文件，再重试。"
            )
            logging.getLogger("llm_interview_lab.desktop").warning(
                "coach_sessions_unavailable profile_id=%s error_type=%s",
                self._profile_id,
                type(error).__name__,
            )
        self.coachChanged.emit()
        self.coachErrorChanged.emit()

    def _sync_active_coach_messages(self) -> None:
        selected = next(
            (
                item
                for item in self._coach_sessions
                if item.get("session_id") == self._active_coach_session_id
            ),
            None,
        )
        self._coach_messages = list(selected.get("messages", [])) if selected else []

    def _coach_session(self, session_id: str | None = None) -> dict[str, Any] | None:
        target = session_id or self._active_coach_session_id
        return next(
            (item for item in self._coach_sessions if item.get("session_id") == target),
            None,
        )

    @staticmethod
    def _coach_provider_matches(session: Mapping[str, Any], requested: str) -> bool:
        """Keep legacy entry points subject to the same provider lock."""

        if not session.get("messages") or not requested:
            return True
        value = str(requested).strip()
        stored = {
            str(session.get("provider_id") or "").strip(),
            str(session.get("provider_kind") or "").strip(),
        }
        return value in stored

    def _persist_coach_sessions(self) -> bool:
        if self._profile_id == "demo":
            return True
        try:
            self._coach_sessions = write_coach_sessions(
                self.repo_root, self._profile_id, self._coach_sessions
            )
            return True
        except Exception as error:
            self._set_coach_error(error)
            return False

    def _mark_coach_session_error(
        self, session: dict[str, Any], value: BaseException | str
    ) -> None:
        """Persist a retryable Coach error without losing the learner turn."""

        message = friendly_error(value)
        session["status"] = "error"
        try:
            session["messages"].append(coach_message("error", message))
            session["updated_at"] = session["messages"][-1]["created_at"]
        except Exception as append_error:
            logging.getLogger("llm_interview_lab.desktop").warning(
                "coach_error_message_unavailable error_type=%s",
                type(append_error).__name__,
            )
        self._persist_coach_sessions()
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        self._set_coach_error(message, persist=False)

    def _set_coach_error(self, error: BaseException | str, *, persist: bool = False) -> None:
        value = friendly_error(error)
        # Give the page a concrete recovery path for local transcript errors.
        if isinstance(error, CoachSessionError) and "provider" not in value.lower():
            value = "本地 Coach 会话未能保存。请检查当前 Profile 的目录权限后重试。"
        self._coach_error = value
        self.coachErrorChanged.emit()
        if persist:
            self._persist_coach_error_message(value)

    def _persist_coach_error_message(self, value: str) -> None:
        session = self._coach_session()
        if session is None:
            return
        try:
            session["messages"].append(coach_message("error", value))
            session["status"] = "error"
            session["updated_at"] = session["messages"][-1]["created_at"]
            self._persist_coach_sessions()
            self._sync_active_coach_messages()
            self.coachChanged.emit()
        except Exception:
            # The visible error already explains the next action; never mask
            # the original provider/local-file failure with a second exception.
            pass

    def _emit_coach_changed(self) -> None:
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        self.stateChanged.emit()

    def _active_problem_id(self) -> str | None:
        value = self._current_task.get("problem_id") if self._current_task else None
        return str(value) if value else None

    def _background(
        self,
        operation: Callable[[], Any],
        complete: Callable[[Any], None],
        failed: Callable[[str], None] | None = None,
    ) -> None:
        operation_token = uuid4().hex
        generation = self._background_generation
        self._background_operations.add(operation_token)
        self._set_busy(True)
        worker = Worker(operation)
        self._workers.add(worker)

        def done(value: Any) -> None:
            self._workers.discard(worker)
            self._background_operations.discard(operation_token)
            self._set_busy(bool(self._background_operations))
            if generation != self._background_generation:
                return
            complete(value)

        failed_handler = failed

        def on_failed(message: str) -> None:
            self._workers.discard(worker)
            self._background_operations.discard(operation_token)
            self._set_busy(bool(self._background_operations))
            if generation != self._background_generation:
                return
            if failed_handler is not None:
                failed_handler(message)
            else:
                self._show_error(message)

        worker.signals.completed.connect(done)
        worker.signals.failed.connect(on_failed)
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

    @Slot(result=bool)
    def loadKnowledge(self) -> bool:
        """Load the research-backed knowledge browser on first explicit use."""

        try:
            # ``include_answers=False`` keeps the list compact; full answer
            # layers are fetched only when a learner selects one card.
            self._knowledge_cards = self.service.knowledge_cards(
                limit=200, include_answers=False
            )
            self._knowledge_detail = {}
            self._knowledge_loaded = True
            self.stateChanged.emit()
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str, result=bool)
    def searchKnowledge(self, query: str) -> bool:
        """Apply deterministic local AND search without mutating learner state."""

        try:
            self._knowledge_cards = self.service.knowledge_cards(
                query=(query or None), limit=200, include_answers=False
            )
            self._knowledge_loaded = True
            self.stateChanged.emit()
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str, result=bool)
    def openKnowledgeCard(self, card_id: str) -> bool:
        """Resolve one card for read-only display in the knowledge browser."""

        try:
            self._knowledge_detail = self.service.knowledge_card_view(card_id)
            self.stateChanged.emit()
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot()
    def refresh(self) -> None:
        # Results from the previous in-memory snapshot must not repaint a
        # freshly loaded Profile. Workers finish naturally, but their callbacks
        # are ignored by the generation check in _background.
        self._background_generation += 1
        self._cancel_coach_stream_for_reload()
        # There is no safe way to merge a worker result into the newly loaded
        # snapshot.  Release the UI lock immediately; the old workers may
        # finish in the background, but their generation token makes their
        # callbacks no-ops.  This also prevents a dead provider from leaving
        # Refresh/No-AI controls permanently disabled.
        self._background_operations.clear()
        self._set_busy(False)
        self._pending_ai_assessment = None
        # A pending AI plan is bound to the current Profile, material SHA and
        # context preview. It must not survive a reload into a different or
        # newly missing Profile.
        self._interview_plan_request = None
        self._interview_plan_preview = {}
        path = profile_paths(self.repo_root, self._profile_id).profile_file
        if not path.is_file():
            self._onboarding = True
            self._dashboard = {}
            self._problems = []
            self._connections = []
            self._connection_error = ""
            self._materials = []
            self._interview = {}
            self._recent_interview = {}
            # A missing Profile must not leave a recording or transcription
            # draft from the previously selected Profile visible in QML.
            self._voice_recorder.reset()
            self._voice_transcription_state = "idle"
            self._voice_transcription_error = ""
            self._voice_transcription_operation_id = ""
            self._voice_question_key = ""
            self._interview_coding_identity = None
            self._interview_coding_tested_revision = ""
            self._interview_coding_test_operation_id = ""
            self._coach_sessions = []
            self._active_coach_session_id = ""
            self._coach_messages = []
            self._coach_error = ""
            self.coachChanged.emit()
            self.coachErrorChanged.emit()
            self.stateChanged.emit()
            return
        try:
            self._load_profile_state()
        except Exception as error:
            self._show_error(error)
        self.stateChanged.emit()

    @Slot(str, str, str, str, str, result=bool)
    def completeOnboarding(
        self,
        profile_id: str,
        role_id: str,
        seniority: str,
        ai_mode: str,
        assessment_json: str,
    ) -> bool:
        """Backward-compatible onboarding entry using an existing safe id."""

        return self._complete_onboarding(
            profile_id, role_id, seniority, ai_mode, assessment_json
        )

    @Slot(str, str, str, str, str, result=bool)
    def completeOnboardingWithDisplayName(
        self,
        display_name: str,
        role_id: str,
        seniority: str,
        ai_mode: str,
        assessment_json: str,
    ) -> bool:
        """Onboarding entry for human names; storage ids stay slug-safe."""

        try:
            profile_id = profile_id_for_display_name(self.repo_root, display_name)
        except Exception as error:
            return self._onboarding_failure("PROFILE_ID_INVALID", "validate", error)
        return self._complete_onboarding(
            profile_id,
            role_id,
            seniority,
            ai_mode,
            assessment_json,
            display_name=display_name.strip(),
        )

    def _complete_onboarding(
        self,
        profile_id: str,
        role_id: str,
        seniority: str,
        ai_mode: str,
        assessment_json: str,
        *,
        display_name: str | None = None,
    ) -> bool:
        if self._onboarding_busy:
            return False
        self._onboarding_busy = True
        self._onboarding_error = ""
        self._onboarding_error_code = ""
        operation_id = uuid4().hex
        self._onboarding_result = {
            "success": False,
            "error_code": "",
            "user_message": "",
            "technical_message": "",
            "recommended_action": "",
            "operation_id": operation_id,
        }
        self.stateChanged.emit()
        stage = "validate"
        try:
            profile_id = profile_id.strip()
            validate_profile_id(profile_id)
            role_id = role_id.strip()
            if not role_id:
                return self._onboarding_failure("ROLE_REQUIRED", stage)
            try:
                assessment = json.loads(assessment_json or "{}")
            except json.JSONDecodeError as error:
                return self._onboarding_failure("ASSESSMENT_INVALID", stage, error)
            if not isinstance(assessment, dict):
                return self._onboarding_failure("ASSESSMENT_INVALID", stage)
            stage = "initialize_profile"
            self.service.initialize_profile(
                profile_id,
                display_name=display_name,
                role_id=role_id,
                seniority=seniority,
                skill_self_assessment=assessment,
                ai_mode=ai_mode,
            )
            self._profile_id = profile_id
            stage = "refresh"
            self._load_profile_state()
            self.stateChanged.emit()
            if self._dashboard.get("unlocks"):
                stage = "open_problem"
                try:
                    self._open_problem(
                        self._dashboard["unlocks"][0]["problem_id"]
                    )
                except Exception as error:
                    logging.getLogger("llm_interview_lab.desktop").error(
                        "onboarding_first_problem_failed error_type=%s",
                        type(error).__name__,
                    )
                    self.navigate("home")
                    self.toast.emit(
                        "学习档案已创建，但首题暂时无法打开。请从首页重新尝试。"
                    )
            else:
                self.navigate("home")
            self._onboarding_result = {
                "success": True,
                "error_code": "",
                "user_message": "学习档案已准备好。",
                "technical_message": "",
                "recommended_action": "继续当前训练。",
                "operation_id": operation_id,
                "profile_id": self._profile_id,
            }
            return True
        except RoleCatalogError as error:
            return self._onboarding_failure("ROLE_NOT_FOUND", stage, error)
        except ApplicationError as error:
            message = str(error)
            if "unsupported seniority" in message:
                code = "SENIORITY_UNSUPPORTED"
            elif "AI mode" in message:
                code = "AI_MODE_INVALID"
            elif "self-assessment" in message:
                code = "ASSESSMENT_INVALID"
            else:
                code = "ONBOARDING_UNEXPECTED"
            return self._onboarding_failure(code, stage, error)
        except WorkspaceError as error:
            message = str(error).lower()
            if "profile id" in message:
                code = "PROFILE_ID_INVALID"
            elif any(
                token in message
                for token in ("invalid profile", "profile.yaml cannot", "does not match")
            ):
                code = "PROFILE_CORRUPTED"
            elif any(
                token in message
                for token in ("template", "schema", "desktop bundle is missing")
            ):
                code = "PUBLIC_ASSETS_MISSING"
            else:
                code = "WORKSPACE_NOT_WRITABLE"
            return self._onboarding_failure(code, stage, error)
        except OSError as error:
            return self._onboarding_failure("WORKSPACE_NOT_WRITABLE", stage, error)
        except Exception as error:
            return self._onboarding_failure("ONBOARDING_UNEXPECTED", stage, error)
        finally:
            self._onboarding_busy = False
            self.stateChanged.emit()

    @Slot(str, str, str, bool, result=bool)
    def addMaterial(
        self, source_url: str, kind: str, title: str, ai_access: bool
    ) -> bool:
        if self._profile_id == "demo":
            self.toast.emit("演示材料完全虚构且为只读。")
            return False
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
            return True
        except Exception as error:
            self._show_error(error)
            return False

    def _open_problem(self, problem_id: str) -> None:
        current = self.service.current_submission(self._profile_id)
        if current is None or current["problem_id"] != problem_id:
            self.service.start_practice(self._profile_id, problem_id)
            current = self.service.current_submission(self._profile_id)
        assert current is not None
        self._current_task = self.service.problem_view(problem_id)
        self._current_task["actions"] = self.service.practice_actions(
            self._profile_id, problem_id
        )
        self._submission = current["text"]
        self._submission_saved_revision = current["sha256"]
        last_test = current.get("last_public_test") or {}
        if (
            last_test.get("status") == "passed"
            and last_test.get("submission_sha256") == current["sha256"]
        ):
            self._tested_revision = current["sha256"]
            self._test_state = "测试通过"
        else:
            self._tested_revision = ""
            self._test_state = "未测试"
        self._test_operation_id = ""
        self._test_identity = (problem_id, current["attempt_id"], self._profile_id)
        self._test_output = "可以开始：完成本次作答后运行公开测试。"
        self._page = "exercise"
        self.stateChanged.emit()
        self.pageChanged.emit()

    @Slot(str, result=bool)
    def openProblem(self, problem_id: str) -> bool:
        try:
            self._open_problem(problem_id)
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str, result=bool)
    def saveSubmission(self, text: str) -> bool:
        if self._profile_id == "demo":
            self._submission = text
            self._submission_saved_revision = self.submissionRevision
            self._test_state = "已保存"
            self.stateChanged.emit()
            return True
        try:
            current_before = self.service.current_submission(self._profile_id)
            if (
                current_before is None
                or current_before["problem_id"] != self._current_task["problem_id"]
            ):
                self._show_error("当前题目或作答轮次已变化，请重新打开这道题后再保存。")
                return False
            current = self.service.save_practice_submission(
                self._profile_id,
                self._current_task["problem_id"],
                text,
                attempt_id=current_before["attempt_id"],
            )
            self._submission = text
            self._submission_saved_revision = current["sha256"]
            if self._tested_revision != current["sha256"]:
                self._test_state = "结果已过期" if self._tested_revision else "已保存"
            self.stateChanged.emit()
            self.toast.emit("已保存到本机。")
            return True
        except Exception as error:
            self._show_error(error)
            self._test_state = "保存失败"
            self.stateChanged.emit()
            return False

    @Slot(str)
    def updateSubmissionDraft(self, value: str) -> None:
        """Keep the editor's latest text visible to every test entry point."""

        if value == self._submission:
            return
        self._submission = value
        if self._tested_revision and self.submissionRevision != self._tested_revision:
            self._test_state = "结果已过期"
        self.stateChanged.emit()

    @Slot()
    def runTests(self) -> None:
        self.runTestsForCurrentSubmission(self._submission)

    @Slot(str)
    def runTestsForCurrentSubmission(self, text: str) -> None:
        if self._busy:
            self.toast.emit("测试正在进行，请稍候。")
            return
        if not self._current_task:
            # A routed/first-launch Exercise page can exist before a learner
            # has selected a problem.  Keep the CTA truthful instead of
            # silently returning from a fake test action.
            self._test_state = "未选择题目"
            self._test_output = "尚未选择题目。请先到 Learn 选择一道可练习的题目。"
            self._show_error("尚未选择题目；请先到 Learn 选择一道可练习的题目。")
            self.stateChanged.emit()
            return
        if self._profile_id == "demo":
            self._submission = text
            self._submission_saved_revision = self.submissionRevision
            self._tested_revision = self.submissionRevision
            self._test_state = "测试通过"
            self._test_output = "5 passed in 0.18s\n\n公开测试：PASS · 掌握状态：尚未达到"
            self.stateChanged.emit()
            return
        problem_id = self._current_task["problem_id"]
        try:
            current = self.service.current_submission(self._profile_id)
        except Exception as error:
            self._test_state = "测试失败"
            self._show_error(error)
            self.stateChanged.emit()
            return
        if current is None:
            self._show_error("当前题目没有可用的作答目录，请重新开始题目。")
            return
        if current["problem_id"] != problem_id:
            self._show_error("当前题目或作答轮次已变化，请重新打开这道题后再运行测试。")
            return
        operation_id = uuid4().hex
        profile_id = self._profile_id
        identity = (problem_id, current["attempt_id"], profile_id)
        self._test_operation_id = operation_id
        self._test_identity = identity
        self._test_state = "正在测试"
        self._submission = text
        self.stateChanged.emit()

        def complete(result) -> None:
            if self._test_operation_id != operation_id:
                return
            try:
                current_now = self.service.current_submission(profile_id)
            except Exception:
                current_now = None
            changed = (
                current_now is None
                or current_now["problem_id"] != problem_id
                or current_now["attempt_id"] != identity[1]
                or self.submissionRevision != result.submission_sha256
                or result.stale
            )
            self._tested_revision = result.submission_sha256
            if not changed:
                self._submission_saved_revision = result.submission_sha256
            self._test_state = "结果已过期" if changed else (
                "测试通过" if result.status == "passed" else "测试失败"
            )
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"公开测试：{result.status.upper()} · 测试版本：{result.tested_revision}"
            )
            self.stateChanged.emit()

        def failed(message: str) -> None:
            if self._test_operation_id != operation_id:
                return
            self._test_state = "测试失败"
            self._test_output = f"测试未运行：{message}"
            self.stateChanged.emit()
            self._show_error(message)

        self._background(
            lambda: self.service.run_practice_tests_for_submission(
                profile_id,
                problem_id,
                text,
                attempt_id=identity[1],
                operation_id=operation_id,
            ),
            complete,
            failed,
        )

    @Slot()
    def submitCurrent(self) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("演示模式不会记录提交。")
            return
        try:
            if (
                not self._tested_revision
                or self.submissionDirty
                or self.submissionRevision != self._tested_revision
            ):
                self._test_state = "结果已过期"
                self.stateChanged.emit()
                self._show_error("当前答案已修改，请先保存并重新运行测试后再提交。")
                return
            result = self.service.submit_practice(
                self._profile_id, self._current_task["problem_id"]
            )
            self.toast.emit(
                "实现已通过；仍需完成自助复盘和口述自答。"
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
        self.startRetentionFor(self._current_task["problem_id"], stage)

    @Slot(str, str, result=bool)
    def startRetentionFor(self, problem_id: str, stage: str) -> bool:
        """Start or resume a due retention attempt independent of the open page."""

        if self._profile_id == "demo":
            self.toast.emit("演示模式不会创建真实复测尝试。")
            return False
        try:
            result = self.service.start_retention(self._profile_id, problem_id, stage)
            current = self.service.current_submission(self._profile_id)
            if current is None or current["problem_id"] != problem_id:
                raise RuntimeError("retention attempt was not created")
            self._current_task = self.service.problem_view(problem_id)
            self._current_task["actions"] = self.service.practice_actions(
                self._profile_id, problem_id
            )
            self._submission = current["text"]
            self._submission_saved_revision = current["sha256"]
            self._tested_revision = ""
            self._test_state = "未测试"
            self._test_identity = (
                problem_id,
                current["attempt_id"],
                self._profile_id,
            )
            self._test_output = (
                f"{stage.upper()} 复测尝试 {result['attempt_id']} 独立创建；"
                "系统没有复制上一次答案。"
            )
            self._page = "exercise"
            self.stateChanged.emit()
            self.pageChanged.emit()
            self.toast.emit(f"已开始经过验证的 {stage.upper()} 间隔复测。")
            return True
        except Exception as error:
            self._show_error(error)
            return False

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

    @Slot(str, str, str, str, str, bool)
    def createNonCodingInterview(
        self,
        role_id: str,
        seniority: str,
        difficulty: str,
        ai_mode: str,
        material_id: str,
        consent: bool,
    ) -> None:
        """Start an explicitly partial interview when only PyTorch is missing."""

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
                material_ids=(material_id,) if material_id else (),
                consent_materials=consent if material_id else False,
                delivery_mode="non_coding_fallback",
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
        # Rebuilding the frozen question snapshot invalidates any provider
        # assessment callback that still belongs to the previous view.
        self._interview_provider_operation_id = ""
        session = self.service.interview_session(self._profile_id, interview_id)
        if session.get("status") in {"completed", "incomplete"}:
            current = {"question": None, "remaining_seconds": 0}
        elif session.get("status") == "paused":
            current = self.service.interview_state(self._profile_id, interview_id)
        else:
            try:
                current = self.service.current_interview(self._profile_id, interview_id)
            except Exception as error:
                # An expired active session still needs a truthful, recoverable UI.
                if session.get("status") == "active" and "expired" in str(error).lower():
                    current = {"question": None, "remaining_seconds": 0}
                else:
                    raise
        questions = session["questions"]
        answered = {
            question["question_id"]
            for question in questions
            if (
                question["question_id"] in session["coding_evidence"]
                if question["kind"] == "coding"
                else question["question_id"] in session["answers"]
            )
        }
        assessed = set(session["assessments"])
        completed = answered.intersection(assessed)
        coding_incomplete = sum(
            1
            for question in questions
            if question["kind"] == "coding"
            and question["question_id"] not in completed
        )
        expired = bool(
            session.get("status") == "active"
            and current.get("question") is None
            and current.get("remaining_seconds", 0) <= 0
        )
        presentation_status = "timed_out" if expired else session["status"]
        self._interview = {
            "interview_id": interview_id,
            # Keep the persisted session untouched until the user confirms
            # finish, but expose a distinct UI state once the local deadline
            # has elapsed. This stops the timer and prevents a misleading
            # "continue" action while still allowing an incomplete report.
            "status": presentation_status,
            "persisted_status": session["status"],
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
            "difficulty": session["difficulty"],
            "blueprint_id": session["blueprint_id"],
            "delivery_mode": session.get("delivery_mode", "full_blueprint"),
            "blueprint_coverage": session.get("blueprint_coverage", {}),
            "ai_mode": session["ai_mode"],
            "material_refs": session["material_refs"],
            "total_questions": len(questions),
            "completed_questions": len(completed),
            "unanswered_questions": len(questions) - len(answered),
            "unscored_questions": len(answered - assessed),
            "coding_incomplete": coding_incomplete,
            # Paused sessions are explicitly recoverable; the Home page uses
            # this flag instead of guessing from a presentation status.
            "resume_available": session["status"] in {"active", "paused"} and not expired,
            "expired": expired,
            "result": self.service.interview_result_view(
                self._profile_id, interview_id
            ),
            **current,
        }
        if session.get("status") in {"completed", "incomplete"}:
            result_view = self._interview.get("result") or {}
            if isinstance(result_view, Mapping):
                self._recent_interview = {
                    key: result_view.get(key)
                    for key in (
                        "interview_id",
                        "status",
                        "completion_status",
                        "overall_score",
                        "finished_at",
                        "summary",
                    )
                    if result_view.get(key) is not None
                }
        question = current.get("question")
        # Include the Profile in the identity: interview ids are allocated per
        # Profile, so the same ``role-interview-0001/q-001`` pair can legally
        # exist in two Profiles.  Audio/transcription state must never cross
        # that boundary when the desktop switches Profiles or reloads.
        voice_question_key = (
            f"{self._profile_id}::{interview_id}::{question.get('question_id', '')}"
            if question
            else f"{self._profile_id}::"
        )
        if voice_question_key != self._voice_question_key:
            self._voice_recorder.reset()
            self._voice_transcription_state = "idle"
            self._voice_transcription_error = ""
            self._voice_transcription_operation_id = ""
            self._voice_question_key = voice_question_key
        if question:
            question_id = question["question_id"]
            answer_record = session.get("answers", {}).get(question_id)
            if answer_record:
                answer_text = ""
                answer_error = ""
                try:
                    answer_text = self.service.interview_answer_text(
                        self._profile_id, interview_id, question_id
                    )
                except ApplicationError as error:
                    answer_error = "已锁定的回答文件缺失或校验失败。请保留本地数据并打开日志目录排查。"
                    logging.getLogger("llm_interview_lab.desktop").error(
                        "interview_answer_unavailable interview_id=%s question_id=%s error_type=%s",
                        interview_id,
                        question_id,
                        type(error).__name__,
                    )
                self._interview["answer_locked"] = True
                self._interview["answer_text"] = answer_text.strip()
                self._interview["answer_corrupted"] = bool(answer_error)
                self._interview["answer_error"] = answer_error
                self._interview["assessment_recorded"] = question_id in session.get("assessments", {})
                self._interview["phase"] = (
                    "error"
                    if answer_error
                    else "followup"
                    if self._interview.get("pending_followup")
                    else "assessment"
                )
            else:
                self._interview["answer_locked"] = False
                self._interview["answer_text"] = ""
                self._interview["answer_corrupted"] = False
                self._interview["answer_error"] = ""
                self._interview["assessment_recorded"] = False
                self._interview["phase"] = "answering"
        if question and question.get("kind") == "coding":
            coding = self.service.current_interview_coding_submission(
                self._profile_id, interview_id
            )
            self._interview["coding_text"] = coding["text"]
            # Coding evidence is keyed by the frozen question id.  Reading
            # the container itself made a restart look like an untested
            # editor even when the persisted grader result was valid.
            evidence = (session.get("coding_evidence") or {}).get(question["question_id"]) or {}
            tested_sha = str(evidence.get("submission_sha256") or "")
            self._interview_coding_tested_revision = tested_sha
            self._interview["coding_tested_revision"] = tested_sha
            self._interview["coding_test_current"] = bool(tested_sha and tested_sha == coding["sha256"])
            self._interview["coding_test_operation_id"] = self._interview_coding_test_operation_id
            self._interview["phase"] = "assessment" if self._interview["coding_test_current"] else "answering"
        else:
            self._interview_coding_tested_revision = ""
            self._interview["coding_tested_revision"] = ""
            self._interview["coding_test_current"] = False
        self.stateChanged.emit()

    @Slot()
    def refreshInterviewClock(self) -> None:
        """Refresh the local session clock without replacing an answer draft."""

        interview_id = self._interview.get("interview_id")
        if not interview_id or self._interview.get("status") != "active":
            return
        try:
            current = self.service.current_interview(self._profile_id, interview_id)
        except Exception as error:
            if "expired" in str(error).lower():
                self._interview["remaining_seconds"] = 0
                self._interview["expired"] = True
                self._interview["resume_available"] = False
                self._interview["persisted_status"] = "active"
                self._interview["status"] = "timed_out"
                self._interview["phase"] = "expired"
                # The core clock is authoritative: once it rejects the active
                # question, the desktop must not leave answer/test actions
                # available against a stale frozen question.
                self._interview["question"] = None
                self.stateChanged.emit()
                return
            logging.getLogger("llm_interview_lab.desktop").warning(
                "interview_clock_refresh_failed error_type=%s",
                type(error).__name__,
            )
            return
        current_question = self._interview.get("question") or {}
        next_question = current.get("question") or {}
        if current_question.get("question_id") != next_question.get("question_id"):
            self._load_interview(interview_id)
            return
        self._interview["remaining_seconds"] = current["remaining_seconds"]
        self.stateChanged.emit()

    @Slot()
    def resumeInterview(self) -> None:
        interview_id = self._interview.get("interview_id")
        if not interview_id:
            return
        try:
            if self._interview.get("status") == "paused":
                self.service.resume_interview(self._profile_id, interview_id)
                self.toast.emit("面试已恢复；计时从暂停时剩余时间继续。")
            elif self._interview.get("status") != "active":
                return
            self._load_interview(interview_id)
            self.navigate("interview")
        except Exception as error:
            self._show_error(error)

    @Slot(result=bool)
    def pauseInterview(self) -> bool:
        interview_id = self._interview.get("interview_id")
        if not interview_id or self._interview.get("status") != "active":
            return False
        try:
            self.service.pause_interview(self._profile_id, interview_id)
            self._load_interview(interview_id)
            self.toast.emit("面试已暂停；恢复后会继续使用剩余时间。")
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str)
    def lockInterviewAnswer(self, answer: str) -> None:
        """Commit a text answer before any rubric or AI assessment is shown."""

        question = self._interview.get("question")
        if not question or question.get("kind") == "coding":
            return
        if self._profile_id == "demo":
            self._interview["answer_locked"] = True
            self._interview["answer_text"] = answer.strip()
            self._interview["phase"] = "assessment"
            self.stateChanged.emit()
            return
        try:
            self.service.answer_interview(
                self._profile_id,
                self._interview["interview_id"],
                question["question_id"],
                answer,
            )
            self._load_interview(self._interview["interview_id"])
        except Exception as error:
            self._show_error(error)

    @Slot(result=bool)
    def startInterviewRecording(self) -> bool:
        """Start a real profile-local recording for the current text round."""

        question = self._interview.get("question") or {}
        if (
            self._profile_id == "demo"
            or self._interview.get("status") != "active"
            or not question
            or question.get("kind") == "coding"
            or self._interview.get("answer_locked")
        ):
            self._show_error("当前问题不能开始录音；你仍可直接输入文字回答。")
            return False
        try:
            interview_id = str(self._interview["interview_id"])
            audio_root = profile_paths(
                self.repo_root, self._profile_id
            ).interviews_root / interview_id / "audio"
            ensure_profile_path_is_safe(
                self.repo_root, self._profile_id, audio_root
            )
            destination = audio_root / (
                f"{question['question_id']}-{uuid4().hex[:10]}.wav"
            )
            ensure_profile_path_is_safe(
                self.repo_root, self._profile_id, destination
            )
            self._voice_transcription_state = "idle"
            self._voice_transcription_error = ""
            self._voice_recorder.start(destination)
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(result=bool)
    def stopInterviewRecording(self) -> bool:
        try:
            self._voice_recorder.stop()
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str, bool)
    def transcribeInterviewRecording(
        self, connection_id: str, consent_remote: bool
    ) -> None:
        """Send only the selected local WAV after one explicit consent."""

        if self._profile_id == "demo":
            self.toast.emit("合成演示不会发送真实音频。")
            return
        if self._voice_transcription_operation_id or self._busy:
            self._show_error("已有录音或转录操作正在进行，请等待完成。")
            return
        audio_path = self._voice_recorder.path
        if self._voice_recorder.state != "recorded" or audio_path is None:
            self._show_error("请先完成一次有效录音；也可以直接输入文字回答。")
            return
        if not consent_remote:
            self._show_error("发送音频到远程转录服务前，需要勾选本次明确授权。")
            return
        profile_id = self._profile_id
        interview_id = str(self._interview.get("interview_id") or "")
        question_id = str((self._interview.get("question") or {}).get("question_id") or "")
        operation_id = uuid4().hex
        self._voice_transcription_operation_id = operation_id
        self._voice_transcription_state = "transcribing"
        self._voice_transcription_error = ""
        self.stateChanged.emit()

        def operation() -> str:
            config = next(
                (
                    item
                    for item in list_connections(self.repo_root, profile_id)
                    if item.connection_id == connection_id
                ),
                None,
            )
            if config is None:
                raise RuntimeError("找不到所选转录连接，请在 AI 连接页重新保存并测试。")
            key = (
                KeyringCredentialStore().load(config.key_reference)
                if config.key_reference
                else None
            )
            transcriber = OpenAICompatibleTranscriber(config, api_key=key)
            return asyncio.run(
                transcriber.transcribe(
                    audio_path,
                    consent_remote=True,
                    language="zh",
                )
            )

        def complete(transcript: str) -> None:
            if (
                self._voice_transcription_operation_id != operation_id
                or self._profile_id != profile_id
                or self._interview.get("interview_id") != interview_id
                or (self._interview.get("question") or {}).get("question_id")
                != question_id
            ):
                return
            self._voice_transcription_operation_id = ""
            self._voice_transcription_state = "transcribed"
            self._voice_transcription_error = ""
            self.stateChanged.emit()
            self.interviewTranscriptReady.emit(transcript)

        def failed(message: str) -> None:
            if self._voice_transcription_operation_id != operation_id:
                return
            self._voice_transcription_operation_id = ""
            self._voice_transcription_state = "error"
            self._voice_transcription_error = friendly_error(message)
            self.stateChanged.emit()
            self._show_error(message)

        self._background(operation, complete, failed)

    @Slot(str, result=bool)
    def saveInterviewCoding(self, text: str) -> bool:
        if self._profile_id == "demo":
            self._interview["coding_text"] = text
            self._interview["coding_test_current"] = False
            self._interview["coding_tested_revision"] = ""
            self._interview_coding_tested_revision = ""
            self.stateChanged.emit()
            return True
        try:
            saved = self.service.save_interview_coding_submission(
                self._profile_id, self._interview["interview_id"], text
            )
            self._interview["coding_text"] = saved.get("text", text)
            self._interview_coding_identity = None
            self._interview_coding_tested_revision = ""
            self._interview["coding_tested_revision"] = ""
            self._interview["coding_test_current"] = False
            self._interview["phase"] = "answering"
            self.stateChanged.emit()
            self.toast.emit("回答已保存到本机的本场面试记录。")
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str, result=bool)
    def runInterviewCoding(self, text: str) -> bool:
        if self._profile_id == "demo":
            self._test_output = "4 passed in 0.16s\n\n代码证据：PASS"
            self._interview["coding_test_current"] = True
            self._interview["coding_tested_revision"] = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()
            self.stateChanged.emit()
            return True
        profile_id = self._profile_id
        interview_id = self._interview["interview_id"]
        question_id = str((self._interview.get("question") or {}).get("question_id") or "")
        if not question_id:
            self._show_error("当前没有可运行的 coding 题目。")
            return False
        try:
            saved = self.service.save_interview_coding_submission(
                profile_id, interview_id, text
            )
        except Exception as error:
            self._show_error(error)
            return False
        operation_id = uuid4().hex
        submission_sha = str(saved.get("sha256") or hashlib.sha256(text.encode("utf-8")).hexdigest())
        identity = (profile_id, interview_id, question_id, operation_id, submission_sha)
        self._interview_coding_identity = identity
        self._interview_coding_test_operation_id = operation_id
        self._interview_coding_tested_revision = ""
        self._interview["coding_tested_revision"] = ""
        self._interview["coding_test_current"] = False
        self._interview["coding_test_operation_id"] = operation_id
        self._interview["phase"] = "answering"
        self.stateChanged.emit()

        def complete(result) -> None:
            if (
                self._profile_id != profile_id
                or self._interview.get("interview_id") != interview_id
                or (self._interview.get("question") or {}).get("question_id") != question_id
                or self._interview_coding_identity != identity
            ):
                return
            try:
                latest = self.service.current_interview_coding_submission(profile_id, interview_id)
                if latest.get("sha256") != submission_sha:
                    return
            except Exception:
                return
            result_sha = str(getattr(result, "submission_sha256", "") or "")
            if result_sha and result_sha != submission_sha:
                return
            result_status = str(getattr(result, "status", "") or "")
            if result_status not in {"passed", "failed"} or bool(
                getattr(result, "stale", False)
            ):
                # A timeout/import/collection/internal error is useful
                # diagnostics, but it is not a scoreable coding round.  Keep
                # the editor in answering state so the UI cannot promise a
                # record action that the core will (correctly) reject.
                self._interview_coding_tested_revision = ""
                self._interview["coding_tested_revision"] = ""
                self._interview["coding_test_current"] = False
                self._interview["coding_test_operation_id"] = operation_id
                self._interview["phase"] = "answering"
                self._test_output = (
                    (result.output + "\n\n" if result.output else "")
                    + f"本地 Grader 未形成可评分证据：{result_status.upper() or 'UNKNOWN'}"
                )
                self.stateChanged.emit()
                self._show_error(
                    "本地 Grader 未能形成可评分证据；请修正环境或代码后重试。"
                )
                return
            self._interview_coding_tested_revision = submission_sha
            self._interview["coding_tested_revision"] = submission_sha
            self._interview["coding_test_current"] = True
            self._interview["coding_test_operation_id"] = operation_id
            self._interview["phase"] = "assessment"
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"代码证据：{result_status.upper()}"
            )
            self.stateChanged.emit()

        def failed(message: str) -> None:
            if self._interview_coding_identity != identity:
                return
            # A worker/fixture failure is different from a failing public
            # assertion: the current revision was not tested and must remain
            # ineligible for the "record round" action.
            self._interview_coding_tested_revision = ""
            self._interview["coding_tested_revision"] = ""
            self._interview["coding_test_current"] = False
            self._interview["phase"] = "answering"
            self._test_output = "本地 Grader 未能运行：" + friendly_error(message)
            self.stateChanged.emit()
            self._show_error(message)

        self._background(
            lambda: self.service.test_interview_coding(
                profile_id, interview_id
            ),
            complete,
            failed,
        )
        return True

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
            evidence = (session.get("coding_evidence") or {}).get(question["question_id"])
            if evidence is None:
                raise RuntimeError("run the interview grader before recording this round")
            current = self.service.current_interview_coding_submission(
                self._profile_id, self._interview["interview_id"]
            )
            tested_sha = str(evidence.get("submission_sha256") or "")
            if not tested_sha or tested_sha != current.get("sha256"):
                raise RuntimeError("代码已修改；请先重新运行本地 Grader，再记录本轮")
            if self._interview.get("coding_test_current") is False and self._interview_coding_tested_revision != tested_sha:
                raise RuntimeError("当前编辑器内容尚未完成有效复测，请先运行本地 Grader")
            passed = evidence["status"] == "passed"
            self.service.score_interview(
                self._profile_id,
                self._interview["interview_id"],
                question["question_id"],
                {
                    name: 5 if passed else 1
                    for name in question["rubric"]["dimensions"]
                },
                evidence=(
                    f"Local Grader objective evidence: status={evidence['status']}; "
                    f"passed={evidence['passed']}; failed={evidence['failed']}; "
                    f"duration_ms={evidence['duration_ms']}; "
                    f"submission_sha256={tested_sha}"
                ),
                source="grader",
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
            if self._interview.get("answer_corrupted"):
                raise RuntimeError("locked interview answer is unavailable; scoring is blocked")
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
        if self._busy or self._interview_provider_operation_id:
            self._show_error("已有评估请求正在处理，请等待完成或检查错误后重试。")
            return
        profile_id = self._profile_id
        interview_id = self._interview["interview_id"]
        question_id = question["question_id"]
        locked_answer = str(self._interview.get("answer_text") or "").strip()
        session = self.service.interview_session(profile_id, interview_id)
        if question_id not in session.get("answers", {}) or not locked_answer:
            self._show_error("请先提交并锁定当前回答，再请求 AI 评估。")
            return
        if session.get("status") != "active" or question_id in session.get("assessments", {}):
            self._show_error("当前问题已经评分或面试已经结束，不能重复请求 AI 评估。")
            return
        dimensions = set(question["rubric"]["dimensions"])
        fatal_issues = set(question["rubric"]["fatal_issues"])
        if not connection_id:
            self._show_error("请选择一个已保存且测试通过的 AI 连接；也可以使用人工评分。")
            return
        operation_id = uuid4().hex
        self._interview_provider_operation_id = operation_id
        self._interview["ai_assessment_state"] = "streaming"
        self._interview["ai_error"] = ""
        self.stateChanged.emit()

        def operation() -> dict[str, Any]:
            config = next(
                (
                    item
                    for item in list_connections(self.repo_root, profile_id)
                    if item.connection_id == connection_id
                ),
                None,
            )
            if config is None:
                raise RuntimeError(
                    "找不到所选 AI 连接。请在 Connections 重新保存并测试，或改用人工评分。"
                )
            key = (
                KeyringCredentialStore().load(config.key_reference)
                if config.key_reference
                else None
            )
            preview = build_role_interview_context_preview(
                self.repo_root,
                profile_id,
                interview_id,
                candidate_answer=locked_answer,
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

        def release() -> None:
            if self._interview_provider_operation_id == operation_id:
                self._interview_provider_operation_id = ""

        def complete(result: dict[str, Any]) -> None:
            try:
                if self._interview_provider_operation_id != operation_id:
                    return
                if (
                    self._profile_id != profile_id
                    or self._interview.get("interview_id") != interview_id
                    or (self._interview.get("question") or {}).get("question_id")
                    != question_id
                ):
                    return
                latest = self.service.interview_session(profile_id, interview_id)
                if latest.get("status") != "active" or question_id in latest.get(
                    "assessments", {}
                ):
                    return
                if result["follow_up"]:
                    self._pending_ai_assessment = {
                        **result,
                        "profile_id": profile_id,
                        "interview_id": interview_id,
                        "question_id": question_id,
                        "operation_id": operation_id,
                    }
                    self._interview["pending_followup"] = result["follow_up"]
                    self._interview["ai_assessment_state"] = "followup"
                    self._interview["ai_error"] = ""
                    self.stateChanged.emit()
                    return
                self.service.score_interview(
                    profile_id,
                    interview_id,
                    question_id,
                    result["scores"],
                    evidence=result["evidence"],
                    source="ai",
                    confidence=result["confidence"],
                    fatal_issues=result["fatal_issues"],
                )
                if (
                    self._profile_id == profile_id
                    and self._interview.get("interview_id") == interview_id
                ):
                    self._interview["ai_assessment_state"] = "complete"
                    self._interview["ai_error"] = ""
                    self._load_interview(interview_id)
            except Exception as error:
                if self._interview_provider_operation_id == operation_id:
                    self._interview["ai_assessment_state"] = "error"
                    self._interview["ai_error"] = friendly_error(error)
                self._show_error(error)
            finally:
                release()
                self.stateChanged.emit()

        def failed(message: str) -> None:
            if self._interview_provider_operation_id != operation_id:
                return
            self._interview["ai_assessment_state"] = "error"
            self._interview["ai_error"] = friendly_error(message)
            release()
            self._show_error(message)
            self.stateChanged.emit()

        self._background(operation, complete, failed)

    @Slot(str)
    def answerAIFollowup(self, answer: str) -> None:
        pending = self._pending_ai_assessment
        if pending is None:
            return
        try:
            profile_id = pending.get("profile_id", self._profile_id)
            if (
                profile_id != self._profile_id
                or self._interview.get("interview_id") != pending["interview_id"]
                or (self._interview.get("question") or {}).get("question_id")
                != pending["question_id"]
            ):
                self._pending_ai_assessment = None
                self._show_error("当前面试问题已经切换，请重新请求 AI 评估。")
                return
            updated = self.service.record_interview_followup(
                profile_id,
                pending["interview_id"],
                parent_question_id=pending["question_id"],
                prompt=pending["follow_up"],
                answer=answer,
            )
            followup_ids = [
                item.get("followup_id")
                for item in updated.get("followups", [])
                if isinstance(item, Mapping)
                and item.get("parent_question_id") == pending["question_id"]
                and item.get("followup_id")
            ]
            self.service.score_interview(
                profile_id,
                pending["interview_id"],
                pending["question_id"],
                pending["scores"],
                evidence=pending["evidence"],
                source="ai",
                confidence=pending["confidence"],
                fatal_issues=pending["fatal_issues"],
                followup_ids=followup_ids,
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
        interview_id = self._interview.get("interview_id")
        if not interview_id:
            self._show_error("当前没有可结束的模拟面试。")
            return
        if self._interview.get("status") in {"completed", "incomplete"}:
            self.toast.emit("这场面试已经结束；可查看报告或开始新场次。")
            return
        try:
            session = self.service.finish_interview(
                self._profile_id,
                interview_id,
                summary="本地结构化模拟面试已完成。",
                confirm_incomplete=True,
            )
            self._load_interview(session["interview_id"])
        except Exception as error:
            self._show_error(error)

    @Slot(str, str, str, str, str, str, result=bool)
    def saveConnection(
        self,
        connection_id: str,
        provider_id: str,
        model: str,
        display_name: str,
        base_url: str,
        api_key: str,
    ) -> bool:
        if self._demo_mode:
            self.toast.emit("合成演示不会保存真实 AI 连接；No-AI 始终可用。")
            return False
        self._connection_error = ""
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
            return True
        except Exception as error:
            # Refresh and filesystem validation can fail in addition to the
            # provider/keyring validators. Keep the form values in QML and
            # expose one actionable error instead of leaking an exception out
            # of a synchronous button handler.
            self._connection_error = (
                friendly_error(error)
                + " 请检查连接字段和本地权限后重试；也可以继续使用 No-AI。"
            )
            self.stateChanged.emit()
            self._show_error(error)
            return False

    @Slot()
    def clearConnectionError(self) -> None:
        if self._connection_error:
            self._connection_error = ""
            self.stateChanged.emit()

    @Slot(str, result=bool)
    def deleteConnection(self, connection_id: str) -> bool:
        if self._demo_mode:
            self.toast.emit("合成演示不会删除或修改真实连接配置。")
            return False
        try:
            deleted = delete_connection(self.repo_root, self._profile_id, connection_id)
            if not deleted:
                self._connection_error = "找不到这条连接；它可能已经被删除。No-AI 仍可使用。"
                self.stateChanged.emit()
                return False
            self._connection_error = ""
            self.refresh()
            self.toast.emit("连接已删除；No-AI 本地训练仍可继续。")
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot(str)
    def testConnection(self, connection_id: str) -> None:
        if self._profile_id == "demo":
            self.toast.emit("虚构演示连接检查完成。")
            return
        if self._busy:
            self.toast.emit("已有本地操作正在进行，请稍候。")
            return

        self._connection_error = ""
        self.stateChanged.emit()
        profile_id = self._profile_id
        generation = self._background_generation
        selected = next(
            (item for item in self._connections if item.get("connection_id") == connection_id),
            None,
        )
        if selected is None:
            self._connection_error = "找不到这条连接。请重新保存配置，或继续使用 No-AI。"
            self.stateChanged.emit()
            return
        selected["ready"] = False
        selected["status"] = "测试中"
        self.stateChanged.emit()
        # A connection can be replaced while a network probe is in flight.
        # Capture its non-secret configuration identity and only apply the
        # result if that exact configuration is still selected when the worker
        # returns.  Never include the key reference or credential in this
        # comparison/log path.
        selected_identity = tuple(
            str(selected.get(field) or "")
            for field in ("provider_id", "model", "display_name", "base_url", "key_reference")
        )

        def operation():
            config = next(
                (
                    item
                    for item in list_connections(self.repo_root, profile_id)
                    if item.connection_id == connection_id
                ),
                None,
            )
            if config is None:
                raise RuntimeError(
                    "找不到这条连接配置。请重新保存并测试，或继续使用 No-AI。"
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
            if generation != self._background_generation or profile_id != self._profile_id:
                return
            current = next(
                (
                    item
                    for item in self._connections
                    if item.get("connection_id") == connection_id
                ),
                None,
            )
            if current is None:
                return
            current_identity = tuple(
                str(current.get(field) or "")
                for field in ("provider_id", "model", "display_name", "base_url", "key_reference")
            )
            if current_identity != selected_identity:
                return
            for item in self._connections:
                if item["connection_id"] == connection_id:
                    item["ready"] = bool(result.ok)
                    item["status"] = "已连接" if result.ok else "连接失败"
            self._connection_error = "" if result.ok else friendly_error(result.message)
            self.stateChanged.emit()
            self.toast.emit("连接成功。" if result.ok else friendly_error(result.message))

        def failed(message: str) -> None:
            if generation != self._background_generation or profile_id != self._profile_id:
                return
            current = next(
                (
                    item
                    for item in self._connections
                    if item.get("connection_id") == connection_id
                ),
                None,
            )
            if current is not None:
                current["ready"] = False
                current["status"] = "连接失败"
            self._connection_error = friendly_error(message)
            self.stateChanged.emit()
            self._show_error(message)

        self._background(operation, complete, failed)

    def _practice_context_preview(
        self,
        mode: str,
        *,
        help_level: str | None,
        include_submission: bool,
        include_test_output: bool,
    ) -> dict[str, Any]:
        if self._profile_id == "demo":
            result = {
                "estimated_tokens": 286,
                "parts": [
                    {"id": "policy", "label": "AI 行为规则", "selected": True, "sensitive": False},
                    {"id": "task", "label": "当前公开题面", "selected": True, "sensitive": False},
                    {"id": "submission", "label": "选中的当前答案", "selected": include_submission, "sensitive": True},
                    {"id": "test", "label": "最近公开测试摘要", "selected": include_test_output, "sensitive": False},
                ],
            }
            history = self._coach_recent_history(self._coach_session() or {})
            result["history_count"] = len(history)
            result["history_message_ids"] = [item.get("message_id", "") for item in history]
            return result
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
            result = {
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
            history = self._coach_recent_history(self._coach_session() or {})
            result["history_count"] = len(history)
            encoded = json.dumps(
                [
                    {
                        "message_id": item.get("message_id", ""),
                        "role": item.get("role", ""),
                        "content": item.get("content", ""),
                    }
                    for item in history
                ],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            result["history_sha256"] = hashlib.sha256(encoded).hexdigest()
            result["history_message_ids"] = [item.get("message_id", "") for item in history]
            return result
        except Exception as error:
            self._show_error(error)
            return {"estimated_tokens": 0, "parts": [], "history_count": 0}

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

    @Slot(str, str, str, str, bool, result="QVariantMap")
    def personalizedInterviewPlanContext(
        self,
        role_id: str,
        seniority: str,
        difficulty: str,
        material_id: str,
        consent: bool,
    ) -> dict[str, Any]:
        """Preview the exact role/material context before any provider call."""

        if self._profile_id == "demo":
            return {
                "estimated_tokens": 320,
                "context_sha256": "d" * 64,
                "parts": [
                    {"id": "policy", "label": "AI 面试计划边界", "selected": True, "sensitive": False},
                    {"id": "blueprint", "label": "岗位与冻结蓝图", "selected": True, "sensitive": False},
                    {"id": "material:resume-demo", "label": "逐场授权的合成简历", "selected": True, "sensitive": True},
                ],
            }
        try:
            if not material_id or not consent:
                raise RuntimeError("首版个性化面试需要选择一份 AI 可读材料并逐场授权。")
            preview = self.service.personalized_interview_context(
                self._profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
                material_ids=(material_id,),
                consent_materials=True,
            )
            return {
                "estimated_tokens": preview.estimated_tokens,
                "context_sha256": hashlib.sha256(
                    preview.selected_text.encode("utf-8")
                ).hexdigest(),
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
            return {"estimated_tokens": 0, "context_sha256": "", "parts": []}

    @Slot(str, str, str, str, str, bool, str)
    def generatePersonalizedInterviewPlan(
        self,
        role_id: str,
        seniority: str,
        difficulty: str,
        connection_id: str,
        material_id: str,
        consent: bool,
        approved_context_sha256: str,
    ) -> None:
        """Use one explicit provider to draft non-coding prompts only."""

        if self._profile_id == "demo":
            self.toast.emit("合成演示不会调用真实 AI 服务。")
            return
        if self._busy or self._interview_plan_request is not None:
            self._show_error("已有面试计划请求正在处理，请等待完成。")
            return
        profile_id = self._profile_id
        request_identity = uuid4().hex
        self._interview_plan_request = {"operation_id": request_identity}
        self._interview_plan_preview = {
            "status": "generating",
            "user_message": "AI 正在根据已确认上下文生成非代码问题；Coding 题仍由本地题库选择。",
        }
        self.stateChanged.emit()

        def operation() -> dict[str, Any]:
            if not connection_id:
                raise RuntimeError("请选择一个已保存并测试通过的 AI 连接。")
            config = next(
                (
                    item
                    for item in list_connections(self.repo_root, profile_id)
                    if item.connection_id == connection_id
                ),
                None,
            )
            if config is None:
                raise RuntimeError("找不到所选 AI 连接，请返回 AI 连接页重新保存并测试。")
            preview = self.service.personalized_interview_context(
                profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
                material_ids=(material_id,),
                consent_materials=consent,
            )
            current_sha = hashlib.sha256(
                preview.selected_text.encode("utf-8")
            ).hexdigest()
            if current_sha != approved_context_sha256:
                raise RuntimeError("上下文在确认后发生变化，请重新预览后再发送。")
            key = (
                KeyringCredentialStore().load(config.key_reference)
                if config.key_reference
                else None
            )
            provider = create_chat_provider(config, api_key=key)

            async def collect() -> str:
                chunks: list[str] = []
                async for event in provider.stream_chat(
                    [
                        {"role": "system", "content": preview.selected_text},
                        {
                            "role": "user",
                            "content": "按 output_schema 生成本场非代码主问题。只返回 JSON，不要生成 Coding 题、答案、评分或未提供的经历事实。",
                        },
                    ]
                ):
                    if event.text:
                        chunks.append(event.text)
                return "".join(chunks)

            response = asyncio.run(collect())
            blueprint = self.service.roles.blueprint_for(role_id, seniority)
            generated = decode_personalized_questions(response, blueprint)
            plan = self.service.preview_personalized_interview(
                profile_id,
                role_id=role_id,
                seniority=seniority,
                difficulty=difficulty,
                generated_questions=generated,
                plan_context_sha256=current_sha,
                material_ids=(material_id,),
                consent_materials=True,
            )
            return {
                "plan": plan,
                "generated_questions": list(generated),
                "context_sha256": current_sha,
                "role_id": role_id,
                "seniority": seniority,
                "difficulty": difficulty,
                "material_id": material_id,
                "consent": True,
            }

        def complete(result: dict[str, Any]) -> None:
            if (
                self._profile_id != profile_id
                or not self._interview_plan_request
                or self._interview_plan_request.get("operation_id") != request_identity
            ):
                return
            self._interview_plan_request = result
            self._interview_plan_preview = {
                **result["plan"],
                "status": "ready",
                "user_message": "计划尚未写入；请检查所有问题后再确认开始。",
            }
            self.stateChanged.emit()
            self.interviewPlanReady.emit()

        def failed(message: str) -> None:
            if (
                self._interview_plan_request
                and self._interview_plan_request.get("operation_id") == request_identity
            ):
                self._interview_plan_request = None
                self._interview_plan_preview = {
                    "status": "error",
                    "user_message": friendly_error(message),
                }
                self.stateChanged.emit()
            self._show_error(message)

        self._background(operation, complete, failed)

    @Slot(result=bool)
    def confirmPersonalizedInterviewPlan(self) -> bool:
        request = self._interview_plan_request
        if not request or "generated_questions" not in request:
            self._show_error("当前没有可确认的 AI 面试计划。")
            return False
        try:
            session = self.service.create_personalized_interview(
                self._profile_id,
                role_id=request["role_id"],
                seniority=request["seniority"],
                difficulty=request["difficulty"],
                generated_questions=request["generated_questions"],
                plan_context_sha256=request["context_sha256"],
                material_ids=(request["material_id"],),
                consent_materials=request["consent"],
            )
            self.service.start_interview(self._profile_id, session["interview_id"])
            self._interview_plan_request = None
            self._interview_plan_preview = {}
            self._load_interview(session["interview_id"])
            self.navigate("interview")
            return True
        except Exception as error:
            self._show_error(error)
            return False

    @Slot()
    def cancelPersonalizedInterviewPlan(self) -> None:
        if self._interview_plan_preview.get("status") == "generating":
            return
        self._interview_plan_request = None
        self._interview_plan_preview = {}
        self.stateChanged.emit()

    # ------------------------------------------------------------------
    # Resumable local Coach workspace
    # ------------------------------------------------------------------

    def _set_coach_streaming(self, value: bool) -> None:
        if self._coach_streaming != value:
            self._coach_streaming = value
            self.coachStreamingChanged.emit()

    def _coach_context_for_turn(
        self,
        mode: str,
        *,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> Any:
        if self._profile_id == "demo":
            # Demo pages never contact a provider.  The synthetic preview is
            # still useful to render the privacy affordance in screenshots.
            return None
        return build_practice_context_preview(
            self.repo_root,
            self.service.catalog,
            self._profile_id,
            mode=mode,
            help_level=help_level if mode == "teacher" else None,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    @staticmethod
    def _coach_recent_history(session: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Return the exact bounded dialogue subset sent to a model."""

        return [
            item
            for item in session.get("messages", [])
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ][-8:]

    @staticmethod
    def _context_record(
        preview: Any, history: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if preview is None:
            references: list[str] = []
            hashes: dict[str, str] = {}
        else:
            references = [part.id for part in preview.parts if part.selected]
            hashes = {
                part.id: part.sha256 for part in preview.parts if part.selected
            }
        if history:
            encoded = json.dumps(
                [
                    {
                        "message_id": item.get("message_id", ""),
                        "role": item.get("role", ""),
                        "content": item.get("content", ""),
                    }
                    for item in history
                ],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            references.append("recent_dialogue")
            hashes["recent_dialogue"] = hashlib.sha256(encoded).hexdigest()
        return {"references": references, "hashes": hashes}

    def _resolve_coach_provider(self, provider_kind: str) -> tuple[Any, str, str, str]:
        """Resolve a saved connection without exposing credentials to QML."""

        configs = list_connections(self.repo_root, self._profile_id)
        requested = (provider_kind or "").strip()
        if requested in {"", "provider", "local"}:
            config = configs[0] if configs else None
        else:
            config = next(
                (
                    item
                    for item in configs
                    if item.connection_id == requested
                    or item.provider_id == requested
                ),
                None,
            )
        if config is None:
            raise RuntimeError(
                "没有可用的已保存 AI 连接。请先在 AI 连接页保存并测试，"
                "或继续使用无需 AI 的本地训练。"
            )
        # ``connections.json`` stores configuration, not a volatile network
        # result.  The controller's current status is therefore the readiness
        # boundary shared with the QML selector; direct/legacy callers cannot
        # accidentally send through an untested or failed connection.
        visible = next(
            (
                item
                for item in self._connections
                if item.get("connection_id") == config.connection_id
            ),
            None,
        )
        if visible is None:
            # The saved file and the UI snapshot can diverge after a refresh
            # or an external edit.  Fail closed instead of treating an
            # unobserved connection as tested and sending a turn through it.
            raise RuntimeError(
                "所选 AI 连接已变化。请刷新 Connections 后重新测试，"
                "或切换 No-AI 本地模式。"
            )
        status = str(visible.get("status") or "")
        if not (
            status in {"connected", "ready"}
            or "已连接" in status
            or "就绪" in status
        ):
            raise RuntimeError(
                "所选 AI 连接尚未测试通过。请先在 AI 连接页点击“测试连接”，"
                "或切换 No-AI 本地模式。"
            )
        key = (
            KeyringCredentialStore().load(config.key_reference)
            if config.key_reference
            else None
        )
        return (
            create_chat_provider(config, api_key=key),
            config.provider_id,
            config.connection_id,
            config.model,
        )

    def _coach_session_summary(self, session: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "session_id": session.get("session_id", ""),
            "profile_id": session.get("profile_id", ""),
            "title": session.get("title", ""),
            "mode": session.get("mode", "coach"),
            "provider_kind": session.get("provider_kind", "none"),
            "provider_id": session.get("provider_id", ""),
            "model": session.get("model", ""),
            "problem_id": session.get("problem_id"),
            "status": session.get("status", "idle"),
            "created_at": session.get("created_at", ""),
            "updated_at": session.get("updated_at", ""),
            "message_count": len(session.get("messages", [])),
            "draft": session.get("draft", ""),
        }

    def _coach_emit_delta(
        self, identity: tuple[str, str, str, str, str], delta: str
    ) -> None:
        """Apply one chunk only if it still belongs to the same request."""

        if not delta or identity[0] != self._profile_id:
            return
        session = self._coach_session(identity[1])
        if session is None:
            # The user may have deleted the session while a provider was
            # streaming.  Late data must not resurrect it or affect another
            # conversation.
            return
        if self._coach_identity != identity:
            return
        if session.get("status") != "streaming":
            return
        if session.get("last_turn", {}).get("operation_id") != identity[2]:
            return
        target = next(
            (
                item
                for item in session.get("messages", [])
                if item.get("message_id") == identity[3]
                and item.get("role") == "assistant"
            ),
            None,
        )
        if target is None:
            return
        target["content"] = str(target.get("content", "")) + delta
        session["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # ``updated_at`` is refreshed by the final write; preserving the
        # message timestamp here avoids importing a second clock into the hot
        # path.  Persisting each chunk makes a process restart recover the
        # latest visible transcript and is acceptable for the bounded UI log.
        persisted = self._persist_coach_sessions()
        if not persisted and self._profile_id != "demo":
            # Do not advertise an idle/complete turn when the durable state
            # could not be written.  Keeping the in-memory transcript visible
            # is useful, but the session remains an explicit error for the
            # next restart.
            session["status"] = "error"
            self._coach_error = "回答已生成但未能保存本地会话；请检查目录权限后重试。"
            self.coachErrorChanged.emit()
        if self._active_coach_session_id == identity[1]:
            self._sync_active_coach_messages()
            self.coachChanged.emit()
        self.coachDelta.emit(
            {
                "profile_id": identity[0],
                "session_id": identity[1],
                "operation_id": identity[2],
                "message_id": identity[3],
                "provider_kind": identity[4],
                "delta": delta,
            }
        )
        self.aiDelta.emit(delta)

    def _coach_turn_finished(
        self,
        identity: tuple[str, str, str, str, str],
        result: Mapping[str, Any] | None = None,
    ) -> None:
        """Finalize a provider turn while guarding every identity component."""

        if identity[0] != self._profile_id:
            return
        session = self._coach_session(identity[1])
        if session is None:
            return
        # A stopped/reloaded/finalized turn is no longer eligible for a
        # terminal callback.  Provider workers can deliver one last event
        # after cancellation; requiring both the live identity and the
        # streaming state prevents that event from changing a newer (or
        # already completed) transcript.
        if self._coach_identity != identity or session.get("status") not in {
            "streaming",
            "error",
        }:
            return
        turn = session.get("last_turn") or {}
        if turn.get("operation_id") != identity[2] or turn.get("message_id") != identity[3]:
            return
        payload = dict(result or {})
        error = payload.get("error")
        cancelled = bool(payload.get("cancelled"))
        if self._coach_cancel_event is not None and self._coach_cancel_event.is_set():
            cancelled = True
        if session.get("status") == "stopped":
            cancelled = True
        if error:
            value = friendly_error(str(error))
            session["status"] = "error"
            try:
                session["messages"].append(coach_message("error", value))
            except Exception:
                pass
            self._coach_error = value
            self.coachErrorChanged.emit()
        elif cancelled:
            session["status"] = "stopped"
            self._coach_error = ""
            self.coachErrorChanged.emit()
        else:
            session["status"] = "idle"
            self._coach_error = ""
            self.coachErrorChanged.emit()
        if session.get("messages"):
            # Use the last message's timestamp as a stable, monotonic local
            # marker; exact wall-clock ordering is not a product fact.
            session["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        persisted = self._persist_coach_sessions()
        if not persisted and self._profile_id != "demo":
            session["status"] = "error"
            self._coach_error = "回答已生成但未能保存本地会话；请检查目录权限后重试。"
            self.coachErrorChanged.emit()
        if self._coach_identity == identity:
            self._coach_identity = None
            self._coach_worker = None
            self._coach_cancel_event = None
            self._coach_operation_id = ""
            self._coach_message_id = ""
            self._set_coach_streaming(False)
            if identity[4] == "codex":
                self._codex_coach_identity = None
                self._codex_coach_turn_id = None
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        if error:
            self.toast.emit("AI 回答失败；可检查连接后点击重试，本地训练仍可继续。")
        elif cancelled:
            self.toast.emit("已停止本次 AI 回答；可以继续编辑或点击重试。")
        else:
            self.toast.emit("AI 回答完成；请核对内容后再决定下一步。")

    def _coach_worker_failed(
        self, identity: tuple[str, str, str, str, str], error: str
    ) -> None:
        self._coach_turn_finished(identity, {"error": error})

    def _begin_codex_turn(self, kind: str, operation_id: str) -> None:
        """Reset the per-turn event gate before issuing ``turn/start``.

        ``CodexEvent`` does not carry our local operation id.  A monotonically
        increasing generation therefore gives callbacks and id-less protocol
        variants a local fence, while concrete server turn ids provide the
        stronger cross-turn check whenever the server supplies them.
        """

        self._codex_turn_generation += 1
        self._codex_active_generation = self._codex_turn_generation
        self._codex_turn_started = False
        self._codex_start_ready = False
        # An unscoped stream is only accepted after this turn explicitly
        # announces ``turn/started``.  This is deliberately false after every
        # completed/stopped turn so a late id-less chunk cannot enter a new
        # transcript.
        self._codex_unscoped_allowed = False
        self._codex_early_events.clear()
        if kind == "coach":
            self._codex_coach_turn_id = f"pending:{operation_id}"
        else:
            self._codex_interview_turn_id = f"pending:{operation_id}"

    def _arm_codex_unscoped_turn(self, kind: str) -> None:
        """Allow an id-less adapter only after its explicit start marker."""

        self._codex_turn_started = True
        expected = (
            self._codex_coach_turn_id if kind == "coach"
            else self._codex_interview_turn_id
        )
        if not expected or str(expected).startswith("pending:"):
            self._codex_unscoped_allowed = True

    def _finish_codex_event_gate(self) -> None:
        """Fence id-less events after a terminal event."""

        self._codex_turn_started = False
        self._codex_start_ready = False
        self._codex_start_response_turn_id = ""
        self._codex_unscoped_allowed = False
        self._codex_active_generation = 0
        self._codex_turn_id = None
        self._codex_early_events.clear()

    def _queue_codex_early_event(self, event: Any, event_turn: Any) -> None:
        """Hold a bounded concrete event until ``turn/start`` is correlated."""

        if not event_turn or not isinstance(event, CodexEvent):
            return
        # A malicious/noisy server must not grow memory while a start request
        # is unresolved. Events beyond the bound are safer to drop than to
        # replay against an unrelated session.
        if len(self._codex_early_events) < 128:
            self._codex_early_events.append(event)

    def _replay_codex_early_events(self, turn_id: str) -> None:
        """Replay only events matching the id returned by this start request."""

        pending = self._codex_early_events
        self._codex_early_events = []
        if not turn_id:
            return
        for event in pending:
            params = event.params if isinstance(event.params, Mapping) else {}
            event_turn = params.get("turnId") or params.get("turn_id")
            nested_turn = params.get("turn")
            if not event_turn and isinstance(nested_turn, Mapping):
                event_turn = nested_turn.get("id")
            if str(event_turn or "") == str(turn_id):
                self._handle_codex_event(event)

    def _invalidate_codex_transport(self, reason: str) -> None:
        """Fail closed when the shared stream cannot identify a turn.

        Codex events are multiplexed across workflows.  Once a turn has been
        replaced, accepting an id-less event would be able to append an old
        answer to the new session.  Ending the transport is safer than
        guessing; the user can reconnect and receive a fresh read-only thread.
        """

        coach_identity = self._codex_coach_identity
        interview_identity = self._codex_interview_identity
        if coach_identity is not None:
            self._coach_turn_finished(coach_identity, {"error": reason})
        if interview_identity is not None:
            self._finish_codex_interview_assessment(interview_identity, error=reason)
        backend = self._codex_backend
        self._codex_backend = None
        self._codex_backend_generation += 1
        self._codex_thread_id = None
        self._codex_threads = {}
        self._codex_thread_mode = None
        self._codex_pump_started = False
        self._codex_drain_pending = False
        self._codex_drain_turn_id = None
        self._codex_drain_waiting_start = False
        self._codex_cancel_pending_operation = ""
        self._codex_cancel_pending_kind = ""
        self._codex_drain_token = ""
        self._finish_codex_event_gate()
        self._ai_status = text("status.ai_offline")
        self.aiStateChanged.emit()
        if backend is not None and self._codex_loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(backend.close(), self._codex_loop)
            except Exception:
                pass
        self.toast.emit(f"{reason} 已断开 Codex；请重新连接后重试。")

    def _schedule_codex_drain_timeout(self, token: str) -> None:
        # A broken App Server may never send a terminal event.  Do not leave
        # the UI permanently unable to start another turn; instead mark the
        # connection offline and require an explicit reconnect.
        QTimer.singleShot(
            5000,
            lambda expected=token: self._expire_codex_drain(expected),
        )

    def _expire_codex_drain(self, token: str) -> None:
        if not self._codex_drain_pending or token != self._codex_drain_token:
            return
        self._codex_drain_pending = False
        self._codex_drain_turn_id = None
        self._codex_cancel_pending_operation = ""
        self._codex_cancel_pending_kind = ""
        self._codex_drain_waiting_start = False
        self._codex_drain_token = ""
        # The stream can no longer be trusted after a missing terminal.  Drop
        # the connection identity so the next user action goes through the
        # normal, explicit connect path instead of mixing generations.
        stale_backend = self._codex_backend
        self._codex_backend = None
        self._codex_backend_generation += 1
        self._codex_thread_id = None
        self._codex_threads = {}
        self._codex_thread_mode = None
        self._codex_turn_id = None
        self._codex_pump_started = False
        self._ai_status = text("status.ai_offline")
        self.aiStateChanged.emit()
        if stale_backend is not None and self._codex_loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    stale_backend.close(), self._codex_loop
                )
            except Exception:
                pass
        self.toast.emit("Codex 未确认停止，连接已置为离线；请重新连接后再试。")

    def _interrupt_codex_turn(self, turn_id: str) -> None:
        if not turn_id or str(turn_id).startswith("pending:"):
            return
        try:
            if self._codex_loop and self._codex_backend and self._codex_thread_id:
                asyncio.run_coroutine_threadsafe(
                    self._codex_backend.interrupt(
                        self._codex_thread_id, str(turn_id)
                    ),
                    self._codex_loop,
                )
        except Exception:
            # The event gate remains the correctness boundary if interrupt
            # itself fails; the timeout will require a clean reconnect.
            pass

    def _release_pending_codex_cancel(
        self, operation_id: str, turn_id: str | None
    ) -> None:
        """Resolve a Stop issued before ``turn/start`` returned."""

        if self._codex_cancel_pending_operation != operation_id:
            return
        if turn_id:
            self._codex_drain_turn_id = str(turn_id)
            self._codex_cancel_pending_operation = ""
            self._codex_cancel_pending_kind = ""
            self._codex_drain_waiting_start = False
            self._codex_drain_token = uuid4().hex
            self._schedule_codex_drain_timeout(self._codex_drain_token)
            self._interrupt_codex_turn(str(turn_id))
            return
        # No server id means there is no safe interrupt/terminal correlation.
        # Do not release the fence on an id-less adapter: a late chunk from
        # the cancelled request would be indistinguishable from a new turn.
        # Drop the transport and require an explicit reconnect instead.
        self._codex_drain_pending = False
        self._codex_drain_turn_id = None
        self._codex_drain_waiting_start = False
        self._codex_cancel_pending_operation = ""
        self._codex_cancel_pending_kind = ""
        self._codex_drain_token = ""
        stale_backend = self._codex_backend
        self._codex_backend = None
        self._codex_backend_generation += 1
        self._codex_thread_id = None
        self._codex_threads = {}
        self._codex_thread_mode = None
        self._codex_pump_started = False
        self._ai_status = text("status.ai_offline")
        self.aiStateChanged.emit()
        if stale_backend is not None and self._codex_loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(stale_backend.close(), self._codex_loop)
            except Exception:
                pass
        self.toast.emit("Codex 未返回可关联的 turn id，已断开以避免旧回答串入；请重新连接后重试。")

    @Slot(object)
    def _handle_codex_turn_started(self, payload: Any) -> None:
        """Apply ``turn/start`` completion on the Qt thread only."""

        if not isinstance(payload, Mapping):
            return
        kind = str(payload.get("kind") or "")
        identity_value = payload.get("identity")
        if not isinstance(identity_value, (tuple, list)):
            return
        identity = tuple(identity_value)
        error = payload.get("error")
        turn_id = payload.get("turn_id")
        turn_id = str(turn_id) if turn_id else None
        operation_id = identity[2] if kind == "coach" else identity[3] if kind == "interview" else ""
        active = (
            self._codex_coach_identity if kind == "coach"
            else self._codex_interview_identity if kind == "interview"
            else None
        )
        if error:
            self._codex_early_events.clear()
            if self._codex_cancel_pending_operation == operation_id:
                self._release_pending_codex_cancel(operation_id, None)
            elif active == identity:
                if kind == "coach":
                    self._coach_worker_failed(identity, str(error))
                else:
                    self._finish_codex_interview_assessment(identity, error=str(error))
            return

        if active == identity:
            self._codex_start_ready = True
            # The response to ``turn/start`` is the strongest correlation
            # available on the App Server protocol.  Bind a concrete id here
            # immediately; waiting for a later ``turn/started`` notification
            # would let a delayed marker from the previous turn claim this
            # operation.  Adapters that omit the id remain explicitly
            # unscoped and are only tolerated for the first turn on a fresh
            # transport (see _handle_codex_event).
            self._codex_start_response_turn_id = turn_id or ""
            if kind == "coach":
                current = self._codex_coach_turn_id
                if turn_id and (not current or str(current).startswith("pending:") or str(current) == turn_id):
                    self._codex_coach_turn_id = turn_id
                elif turn_id and current != turn_id:
                    self._codex_early_events.clear()
                    return
            else:
                current = self._codex_interview_turn_id
                if turn_id and (not current or str(current).startswith("pending:") or str(current) == turn_id):
                    self._codex_interview_turn_id = turn_id
                elif turn_id and current != turn_id:
                    self._codex_early_events.clear()
                    return
            if turn_id:
                self._codex_turn_id = turn_id
                self._codex_turn_started = True
                self._codex_unscoped_allowed = False
            # Replay only events carrying the exact id returned by this
            # request. Any buffered marker from an older turn is discarded.
            self._replay_codex_early_events(turn_id or "")
            return

        # Stop may have cleared the live identity while ``turn/start`` was in
        # flight.  Bind/interrupt only this operation, never a later turn.
        if self._codex_cancel_pending_operation == operation_id:
            self._release_pending_codex_cancel(operation_id, turn_id)

    def _start_codex_coach_turn(
        self,
        session: dict[str, Any],
        *,
        user_text: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
        append_user: bool,
    ) -> bool:
        """Start a read-only Codex turn and persist its visible transcript."""

        # The App Server event stream is shared by Coach and Interview.  Keep
        # one scoped turn at a time so an event without a server turn id can
        # never be routed to the other workflow (and so Stop/Approval always
        # names exactly one operation).
        if self._codex_interview_identity is not None:
            self._set_coach_error("Codex 正在评估面试回答，请先等待或停止后再使用 Coach。")
            return False
        if self._codex_thread_mode not in {None, "coach", "teacher", "reviewer"}:
            self._set_coach_error(
                "当前 Codex 连接属于其他工作流；请先连接“教练模式”后再发送。"
            )
            return False
        if self._codex_drain_pending:
            self._set_coach_error("Codex 正在确认上一次停止，请收到确认后再重试。")
            return False

        if append_user:
            try:
                session["messages"].append(
                    coach_message(
                        "user", user_text,
                        metadata={"mode": session["mode"], "provider_kind": "codex"},
                    )
                )
            except Exception as error:
                self._set_coach_error(error)
                return False
        if self._codex_backend is None or not self._codex_thread_id:
            value = "Codex 尚未连接。请先点击“连接 Codex”；本地训练和手动面试仍可继续。"
            session["status"] = "error"
            session["last_turn"] = {
                "profile_id": self._profile_id,
                "session_id": session["session_id"],
                "operation_id": "",
                "message_id": session["messages"][-1]["message_id"] if session.get("messages") else "",
                "provider_kind": "codex",
                "provider_id": "codex",
                "model": "",
                "mode": session["mode"],
                "help_level": help_level,
                "include_submission": bool(include_submission),
                "include_test_output": bool(include_test_output),
            }
            try:
                session["messages"].append(coach_message("error", value))
                self._persist_coach_sessions()
                self._sync_active_coach_messages()
                self.coachChanged.emit()
            except Exception:
                pass
            self._set_coach_error(value)
            return False
        try:
            preview = self._coach_context_for_turn(
                session["mode"],
                help_level=help_level,
                include_submission=include_submission,
                include_test_output=include_test_output,
            )
            if preview is None:
                raise RuntimeError("演示模式不会连接真实 AI")
        except Exception as error:
            self._mark_coach_session_error(session, error)
            return False
        if append_user and not session.get("messages", [])[-1].get("role") == "user":
            try:
                session["messages"].append(
                    coach_message(
                        "user",
                        user_text,
                        metadata={"mode": session["mode"], "provider_kind": "codex"},
                    )
                )
            except Exception as error:
                self._set_coach_error(error)
                return False
        history = self._coach_recent_history(session)
        # The current request is persisted before this function is called. It
        # is sent once as the explicit learner turn below; avoid duplicating it
        # in the bounded context dialogue.
        if (
            history
            and history[-1].get("role") == "user"
            and history[-1].get("content") == user_text
        ):
            history = history[:-1]
        assistant = coach_message(
            "assistant",
            "",
            metadata={"provider_kind": "codex", "sandbox": "readOnly"},
        )
        session["messages"].append(assistant)
        operation_id = uuid4().hex
        session["provider_kind"] = "codex"
        session["provider_id"] = "codex"
        session["model"] = ""
        session["context"] = self._context_record(preview, history)
        session["status"] = "streaming"
        session["last_turn"] = {
            "profile_id": self._profile_id,
            "session_id": session["session_id"],
            "operation_id": operation_id,
            "message_id": assistant["message_id"],
            "provider_kind": "codex",
            "provider_id": "codex",
            "model": "",
            "mode": session["mode"],
            "help_level": help_level,
            "include_submission": bool(include_submission),
            "include_test_output": bool(include_test_output),
        }
        if not self._persist_coach_sessions():
            session["status"] = "error"
            self._sync_active_coach_messages()
            self.coachChanged.emit()
            return False
        identity = (
            self._profile_id,
            session["session_id"],
            operation_id,
            assistant["message_id"],
            "codex",
        )
        self._coach_identity = identity
        self._codex_coach_identity = identity
        self._begin_codex_turn("coach", operation_id)
        self._coach_operation_id = operation_id
        self._coach_message_id = assistant["message_id"]
        self._set_coach_streaming(True)
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        prompt = preview.selected_text + "\n\n## Recent Coach dialogue\n" + "\n".join(
            f"{item['role']}: {item['content']}" for item in history
        )
        prompt += "\n\n## Learner request\n" + user_text
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._codex_backend.start_turn(self._codex_thread_id, prompt),
                self._ensure_codex_loop(),
            )
        except Exception as error:
            self._coach_turn_finished(identity, {"error": str(error)})
            return False
        def on_started(value, token=identity) -> None:
            try:
                error = value.exception()
                if error:
                    self._codexTurnStarted.emit(
                        {"kind": "coach", "identity": token, "error": str(error)}
                    )
                    return
                response = value.result() or {}
                turn = response.get("turn") if isinstance(response, Mapping) else None
                turn_id = (turn or {}).get("id") if isinstance(turn, Mapping) else None
                self._codexTurnStarted.emit(
                    {"kind": "coach", "identity": token, "turn_id": turn_id}
                )
            except Exception as error:
                self._codexTurnStarted.emit(
                    {"kind": "coach", "identity": token, "error": str(error)}
                )

        future.add_done_callback(on_started)
        return True

    def _start_provider_coach_turn(
        self,
        session: dict[str, Any],
        *,
        user_text: str,
        provider_kind: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
        append_user: bool,
    ) -> bool:
        # Persist the learner's request before resolving a remote adapter.  A
        # missing key/connection is still a real, retryable turn rather than
        # silently dropping what the learner typed.
        user: dict[str, Any] | None = None
        if append_user:
            try:
                user = coach_message(
                    "user",
                    user_text,
                    metadata={"mode": session["mode"], "provider_kind": provider_kind or "provider"},
                )
                session["messages"].append(user)
            except Exception as error:
                self._set_coach_error(error)
                return False
        try:
            provider, provider_id, connection_id, model = self._resolve_coach_provider(
                provider_kind
            )
            preview = self._coach_context_for_turn(
                session["mode"],
                help_level=help_level,
                include_submission=include_submission,
                include_test_output=include_test_output,
            )
            if preview is None:
                raise RuntimeError("演示模式不会连接真实 AI")
        except Exception as error:
            value = friendly_error(error)
            session["status"] = "error"
            if user is not None:
                session["last_turn"] = {
                    "profile_id": self._profile_id,
                    "session_id": session["session_id"],
                    "operation_id": "",
                    "message_id": user["message_id"],
                    "provider_kind": provider_kind or "provider",
                    "provider_id": provider_kind or "",
                    "model": "",
                    "mode": session["mode"],
                    "help_level": help_level,
                    "include_submission": bool(include_submission),
                    "include_test_output": bool(include_test_output),
                }
                try:
                    session["messages"].append(coach_message("error", value))
                except Exception:
                    pass
                self._persist_coach_sessions()
                self._sync_active_coach_messages()
                self.coachChanged.emit()
            self._set_coach_error(error, persist=False)
            return False

        user_messages = self._coach_recent_history(session)
        # The current empty assistant placeholder is added after history is
        # assembled, so it can never be sent back to the provider.
        history = user_messages[-8:]
        assistant = coach_message(
            "assistant",
            "",
            metadata={
                "provider_kind": provider_id,
                "connection_id": connection_id,
                "model": model,
            },
        )
        session["messages"].append(assistant)
        operation_id = uuid4().hex
        session["provider_kind"] = provider_id
        session["provider_id"] = connection_id
        session["model"] = model
        session["context"] = self._context_record(preview, history)
        session["status"] = "streaming"
        session["last_turn"] = {
            "profile_id": self._profile_id,
            "session_id": session["session_id"],
            "operation_id": operation_id,
            "message_id": assistant["message_id"],
            "provider_kind": provider_id,
            "provider_id": connection_id,
            "model": model,
            "mode": session["mode"],
            "help_level": help_level,
            "include_submission": bool(include_submission),
            "include_test_output": bool(include_test_output),
        }
        if not self._persist_coach_sessions():
            session["status"] = "error"
            self._sync_active_coach_messages()
            self.coachChanged.emit()
            return False
        identity = (
            self._profile_id,
            session["session_id"],
            operation_id,
            assistant["message_id"],
            provider_id,
        )
        self._coach_identity = identity
        self._coach_operation_id = operation_id
        self._coach_message_id = assistant["message_id"]
        self._coach_cancel_event = None
        self._set_coach_streaming(True)
        self._sync_active_coach_messages()
        self.coachChanged.emit()

        provider_messages = [
            {"role": "system", "content": preview.selected_text},
            *[
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item.get("content")
            ],
        ]

        def operation(progress: Callable[[str], None], cancel: threading.Event) -> dict[str, Any]:
            async def collect() -> dict[str, Any]:
                chunks: list[str] = []
                try:
                    async for event in provider.stream_chat(provider_messages):
                        if cancel.is_set():
                            return {"text": "".join(chunks), "cancelled": True}
                        if event.text:
                            chunks.append(event.text)
                            progress(event.text)
                except asyncio.CancelledError:
                    return {"text": "".join(chunks), "cancelled": True}
                except Exception as error:
                    return {"text": "".join(chunks), "error": str(error)}
                return {"text": "".join(chunks), "cancelled": cancel.is_set()}

            return asyncio.run(collect())

        worker = StreamingWorker(operation)
        self._coach_worker = worker
        self._coach_cancel_event = worker.cancel_event
        worker.signals.progress.connect(
            lambda value, token=identity: self._coach_emit_delta(token, str(value))
        )
        worker.signals.completed.connect(
            lambda value, token=identity: self._coach_turn_finished(token, value)
        )
        worker.signals.failed.connect(
            lambda value, token=identity: self._coach_worker_failed(token, value)
        )
        self._thread_pool.start(worker)
        return True

    def _start_coach_turn(
        self,
        *,
        message: str,
        provider_kind: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
        append_user: bool = True,
    ) -> bool:
        if not isinstance(message, str) or not message.strip():
            self._set_coach_error("请输入问题后再发送。")
            return False
        if len(message) > 50_000:
            self._set_coach_error("问题过长，请缩短后再发送。")
            return False
        if self._coach_streaming:
            self._set_coach_error("当前回答仍在生成，请先停止或等待完成。")
            return False
        session = self._coach_session()
        if session is None:
            if not self.createCoachSession(
                "coach", provider_kind, self._active_problem_id(), ""
            ):
                return False
            session = self._coach_session()
        assert session is not None
        if session.get("profile_id") != self._profile_id:
            self._set_coach_error("当前会话不属于当前 Profile，已拒绝发送。")
            return False
        if append_user and session.get("messages") and provider_kind:
            if not self._coach_provider_matches(session, provider_kind):
                self._set_coach_error(
                    "本地会话已有消息，不能切换 Provider；请新建会话后再切换。"
                )
                return False
        if append_user and session.get("messages") and session.get("mode") not in {
            "coach",
            "teacher",
            "reviewer",
        }:
            self._set_coach_error("会话模式无效，请新建会话。")
            return False
        selected_provider = (provider_kind or session.get("provider_id") or "none").strip().lower()
        if selected_provider in {"none", "local", "demo"}:
            return self._complete_local_coach_turn(session, message.strip(), append_user)
        if selected_provider == "codex":
            return self._start_codex_coach_turn(
                session,
                user_text=message.strip(),
                help_level=help_level,
                include_submission=include_submission,
                include_test_output=include_test_output,
                append_user=append_user,
            )
        return self._start_provider_coach_turn(
            session,
            user_text=message.strip(),
            provider_kind=(
                provider_kind
                or session.get("provider_id")
                or session.get("provider_kind")
                or "none"
            ),
            help_level=help_level,
            include_submission=include_submission,
            include_test_output=include_test_output,
            append_user=append_user,
        )

    def _complete_local_coach_turn(
        self, session: dict[str, Any], user_text: str, append_user: bool
    ) -> bool:
        """Truthful No-AI path that never invokes a provider or edits answers."""

        try:
            if append_user:
                session["messages"].append(
                    coach_message("user", user_text, metadata={"provider_kind": "none"})
                )
            response = (
                "当前为 No-AI 本地模式，未调用任何模型。你可以继续阅读题面、编辑答案、"
                "运行公开测试或保存草稿；需要模型反馈时，请先在 Connections 保存并测试一个 Provider。"
            )
            session["messages"].append(
                coach_message("assistant", response, metadata={"provider_kind": "none"})
            )
            session["provider_kind"] = "none"
            session["provider_id"] = "none"
            session["status"] = "idle"
            session["last_turn"] = {
                "profile_id": self._profile_id,
                "session_id": session["session_id"],
                "operation_id": uuid4().hex,
                "message_id": session["messages"][-1]["message_id"],
                "provider_kind": "none",
                "provider_id": "none",
                "model": "",
                "mode": session["mode"],
            }
            if not self._persist_coach_sessions():
                return False
            self._sync_active_coach_messages()
            self._coach_error = ""
            self.coachErrorChanged.emit()
            self.coachChanged.emit()
            self.toast.emit("No-AI 本地模式已记录；没有调用模型或修改答案。")
            return True
        except Exception as error:
            self._set_coach_error(error)
            return False

    @Slot(str, str, str, str, result=bool)
    def createCoachSession(
        self,
        mode: str = "coach",
        provider_kind: str = "none",
        problem_id: str = "",
        title: str = "",
    ) -> bool:
        if self._coach_streaming:
            self._set_coach_error("当前回答仍在生成，请先停止后再新建会话。")
            return False
        if mode not in {"coach", "teacher", "reviewer"}:
            self._set_coach_error("会话模式无效，请新建会话并选择教练、讲解或审查。")
            return False
        if self._profile_id == "demo":
            session_id = f"coach-demo-{uuid4().hex[:12]}"
            session = {
                "session_id": session_id,
                "profile_id": "demo",
                "title": title.strip() or "新建演示会话",
                "mode": mode,
                "provider_kind": provider_kind or "demo",
                "provider_id": provider_kind or "demo",
                "model": "",
                "problem_id": problem_id or self._active_problem_id(),
                "status": "idle",
                "created_at": "2026-08-30T08:00:00+00:00",
                "updated_at": "2026-08-30T08:00:00+00:00",
                "draft": "",
                "context": {"references": [], "hashes": {}},
                "messages": [],
                "last_turn": None,
            }
        else:
            try:
                session = new_coach_session(
                    self.repo_root,
                    self._profile_id,
                    mode=mode,
                    provider_kind=provider_kind or "none",
                    problem_id=problem_id or self._active_problem_id(),
                    title=title or None,
                )
            except Exception as error:
                self._set_coach_error(error)
                return False
        self._coach_sessions = [session] + [
            item
            for item in self._coach_sessions
            if item.get("session_id") != session.get("session_id")
        ]
        self._active_coach_session_id = session["session_id"]
        self._sync_active_coach_messages()
        self._coach_error = ""
        self.coachErrorChanged.emit()
        self.coachChanged.emit()
        return True

    @Slot(str, result=bool)
    def selectCoachSession(self, session_id: str) -> bool:
        if self._coach_streaming and session_id != self._active_coach_session_id:
            self._set_coach_error("当前回答仍在生成，请先停止后再切换会话。")
            return False
        session = self._coach_session(session_id)
        if session is None or session.get("profile_id") != self._profile_id:
            self._set_coach_error("找不到这个本地 Coach 会话；请重新选择当前 Profile 的会话。")
            return False
        self._active_coach_session_id = session_id
        self._sync_active_coach_messages()
        self._coach_error = ""
        self.coachErrorChanged.emit()
        self.coachChanged.emit()
        return True

    @Slot(str, result=bool)
    def deleteCoachSession(self, session_id: str) -> bool:
        session = self._coach_session(session_id)
        if session is None:
            return False
        if self._coach_identity and self._coach_identity[1] == session_id:
            self.stopCoachTurn()
        self._coach_sessions = [
            item for item in self._coach_sessions if item.get("session_id") != session_id
        ]
        if self._profile_id != "demo" and not self._persist_coach_sessions():
            return False
        if self._active_coach_session_id == session_id:
            self._active_coach_session_id = (
                self._coach_sessions[0]["session_id"] if self._coach_sessions else ""
            )
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        return True

    @Slot(str)
    def updateCoachDraft(self, value: str) -> None:
        session = self._coach_session()
        if session is None or not isinstance(value, str):
            return
        if len(value) > 200_000:
            self._set_coach_error("草稿过长，未保存。")
            return
        session["draft"] = value
        if self._profile_id != "demo":
            self._persist_coach_sessions()
        self.coachChanged.emit()

    @Slot()
    def clearCoachError(self) -> None:
        if self._coach_error:
            self._coach_error = ""
            self.coachErrorChanged.emit()

    @Slot(str, result=bool)
    def copyCoachText(self, value: str) -> bool:
        """Copy explicitly selected Coach text through the native clipboard."""

        if not isinstance(value, str) or not value:
            return False
        try:
            clipboard = QGuiApplication.clipboard()
            if clipboard is None:
                return False
            clipboard.setText(value)
            self.toast.emit("已复制到剪贴板。")
            return True
        except Exception as error:
            self._set_coach_error(error)
            return False

    @Slot(str, str, bool, bool, result=bool)
    def sendCoachTurn(
        self,
        message: str,
        provider_kind: str = "",
        include_submission: bool = False,
        include_test_output: bool = True,
    ) -> bool:
        session = self._coach_session()
        if session is None:
            if not self.createCoachSession(
                "coach", provider_kind or "none", self._active_problem_id(), ""
            ):
                return False
            session = self._coach_session()
        assert session is not None
        return self._start_coach_turn(
            message=message,
            provider_kind=(
                provider_kind
                or session.get("provider_id")
                or session.get("provider_kind")
                or "none"
            ),
            help_level="",
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    @Slot(str, str, bool, bool, bool, result=bool)
    def sendCoachTurnDetailed(
        self,
        message: str,
        mode: str,
        help_level: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> bool:
        """Mode-aware entry used by the QML Coach page."""

        session = self._coach_session()
        if session is None or (not session.get("messages") and session.get("mode") != mode):
            if session is not None and session.get("messages"):
                self._set_coach_error("首条消息后不能切换模式，请新建会话。")
                return False
            if not self.createCoachSession(
                mode, "none", self._active_problem_id(), ""
            ):
                return False
        elif session.get("mode") != mode:
            self._set_coach_error("会话模式已锁定，请新建会话后切换。")
            return False
        return self._start_coach_turn(
            message=message,
            provider_kind=(session or self._coach_session() or {}).get("provider_id", "provider"),
            help_level=help_level,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    @Slot(str, str, str, str, bool, bool, result=bool)
    def sendCoachTurnConfigured(
        self,
        message: str,
        mode: str,
        help_level: str,
        provider_kind: str,
        include_submission: bool,
        include_test_output: bool,
    ) -> bool:
        """Send one turn with all UI selectors explicit.

        The historical four-argument ``sendCoachTurn`` remains intact for
        older clients; the new page uses this explicit boundary so a
        connection/model choice cannot be silently replaced by the first
        saved adapter.
        """

        if mode not in {"coach", "teacher", "reviewer"}:
            self._set_coach_error("会话模式无效，请新建会话。")
            return False
        session = self._coach_session()
        if session is None:
            if not self.createCoachSession(
                mode, provider_kind or "none", self._active_problem_id(), ""
            ):
                return False
            session = self._coach_session()
        elif session.get("mode") != mode:
            if session.get("messages"):
                self._set_coach_error("首条消息后不能切换模式，请新建会话。")
                return False
            session["mode"] = mode
        if session is None:
            return False
        # Provider choice is part of a transcript's context identity.  Once a
        # learner has sent a turn, changing it in a stale/automated client
        # would make retry semantics and the visible context misleading.
        if session.get("messages") and provider_kind:
            stored_provider = str(
                session.get("provider_id") or session.get("provider_kind") or "none"
            )
            requested_provider = str(provider_kind)
            if requested_provider != stored_provider:
                self._set_coach_error(
                    "本地会话已有消息，不能切换 Provider；请新建会话后再切换。"
                )
                return False
        if provider_kind:
            session["provider_id"] = provider_kind
            session["provider_kind"] = provider_kind
            self._persist_coach_sessions()
        return self._start_coach_turn(
            message=message,
            provider_kind=provider_kind or session.get("provider_id", "provider"),
            help_level=help_level,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    @Slot(result=bool)
    def stopCoachTurn(self) -> bool:
        if not self._coach_streaming or self._coach_identity is None:
            return False
        identity = self._coach_identity
        codex_turn = self._codex_coach_turn_id
        if self._coach_worker is not None:
            self._coach_worker.cancel_event.set()
        session = self._coach_session(identity[1])
        if session is not None:
            session["status"] = "stopped"
            self._persist_coach_sessions()
        # Codex has a native interrupt path; provider adapters observe the
        # cancellation event and finish on their next chunk.
        if identity[4] == "codex":
            self._codex_drain_pending = True
            self._codex_drain_token = uuid4().hex
            if codex_turn and str(codex_turn).startswith("pending:"):
                # ``turn/start`` may still be in flight.  Do not let the first
                # terminal event from a later request satisfy this fence; the
                # start callback will bind a real id (or explicitly release
                # the fence when the adapter cannot provide one).
                self._codex_drain_turn_id = None
                self._codex_cancel_pending_operation = identity[2]
                self._codex_cancel_pending_kind = "coach"
                self._codex_drain_waiting_start = True
            else:
                self._codex_drain_turn_id = codex_turn
                self._codex_cancel_pending_operation = ""
                self._codex_cancel_pending_kind = ""
                self._codex_drain_waiting_start = False
                self._schedule_codex_drain_timeout(self._codex_drain_token)
            # Preserve the scoped turn id while invalidating the UI identity;
            # the native interrupt is best effort and late events must be
            # dropped even if the request itself races this cleanup.
            # A pending sentinel is local bookkeeping, not an App Server
            # turn id; sending it as an interrupt can cancel an unrelated
            # server turn on adapters that accept arbitrary strings.
            if codex_turn and not str(codex_turn).startswith("pending:"):
                try:
                    if (
                        self._codex_loop
                        and self._codex_backend
                        and self._codex_thread_id
                    ):
                        asyncio.run_coroutine_threadsafe(
                            self._codex_backend.interrupt(
                                self._codex_thread_id, codex_turn
                            ),
                            self._codex_loop,
                        )
                except Exception:
                    pass
            self._codex_coach_identity = None
            self._codex_coach_turn_id = None
        self._coach_identity = None
        self._coach_worker = None
        self._coach_cancel_event = None
        self._coach_operation_id = ""
        self._coach_message_id = ""
        self._finish_codex_event_gate()
        self._set_coach_streaming(False)
        self._coach_error = ""
        self.coachErrorChanged.emit()
        self._sync_active_coach_messages()
        self.coachChanged.emit()
        return True

    @Slot(result=bool)
    def retryCoachTurn(self) -> bool:
        session = self._coach_session()
        if session is None:
            self._set_coach_error("没有可重试的 Coach 会话。")
            return False
        if self._coach_streaming:
            self._set_coach_error("请先停止当前回答，再重试。")
            return False
        last_turn = session.get("last_turn") or {}
        message_id = last_turn.get("message_id")
        users = [
            item
            for item in session.get("messages", [])
            if item.get("role") == "user"
        ]
        if not users:
            self._set_coach_error("当前会话还没有可重试的问题。")
            return False
        user_text = users[-1].get("content", "")
        # Keep the previous assistant/error as an auditable local attempt;
        # the new assistant message gets a fresh operation/message identity.
        return self._start_coach_turn(
            message=user_text,
            provider_kind=last_turn.get("provider_id")
            or last_turn.get("provider_kind")
            or session.get("provider_id", "provider"),
            help_level=last_turn.get("help_level", ""),
            include_submission=bool(last_turn.get("include_submission", False)),
            include_test_output=bool(last_turn.get("include_test_output", True)),
            append_user=False,
        )

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
        # Keep the historical entry point for older QML/CLI clients while
        # routing its transcript through the resumable session workspace.
        session = self._coach_session()
        if session is None:
            if not self.createCoachSession(
                mode, connection_id, self._active_problem_id(), ""
            ):
                return
            session = self._coach_session()
        elif session.get("mode") != mode and session.get("messages"):
            self._set_coach_error("会话模式已锁定，请新建会话后切换。")
            return
        assert session is not None
        if not self._coach_provider_matches(session, connection_id):
            self._set_coach_error(
                "本地会话已有消息，不能切换 Provider；请新建会话后再切换。"
            )
            return
        if not session.get("messages"):
            session["provider_id"] = connection_id
            session["provider_kind"] = connection_id or "provider"
            self._persist_coach_sessions()
        self._start_coach_turn(
            message=message,
            provider_kind=connection_id,
            help_level=help_level,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

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

    async def _pump_codex(self, backend: Any | None = None) -> None:
        # Keep the transport loop deliberately tiny.  ``CodexEvent`` is
        # immutable and the signal crosses into the GUI thread before any
        # identity, transcript, or QML-visible property is changed.
        backend = backend or self._codex_backend
        if backend is None:
            return
        try:
            async for event in backend.events():
                self._codexEventReceived.emit(event)
        finally:
            # The backend may close without a terminal turn event (for
            # example, a crashed Codex process).  Hand the cleanup back to the
            # Controller's Qt thread so reconnecting cannot reuse a dead pump.
            self._codexPumpEnded.emit(backend)

    @Slot(object)
    def _handle_codex_pump_ended(self, backend: Any) -> None:
        if self._shutdown_done or backend is not self._codex_backend:
            return
        self._codex_pump_started = False
        self._codex_backend = None
        self._codex_backend_generation += 1
        self._codex_thread_id = None
        self._codex_threads = {}
        self._codex_thread_mode = None
        self._codex_turn_id = None
        self._codex_drain_pending = False
        self._codex_drain_turn_id = None
        self._codex_drain_waiting_start = False
        self._codex_cancel_pending_operation = ""
        self._codex_cancel_pending_kind = ""
        self._codex_drain_token = ""
        self._finish_codex_event_gate()
        self._ai_status = text("status.ai_offline")
        self.aiStateChanged.emit()
        # A dead stream must not leave either workflow visually streaming.
        if self._codex_coach_identity is not None:
            identity = self._codex_coach_identity
            self._coach_turn_finished(identity, {"error": "Codex 连接已断开，请重新连接后重试。"})
        if self._codex_interview_identity is not None:
            identity = self._codex_interview_identity
            self._finish_codex_interview_assessment(
                identity, error="Codex 连接已断开，请重新连接后重试。"
            )
        self.toast.emit("Codex 连接已断开；请重新连接，或继续使用 No-AI。")

    @Slot(object)
    def _handle_codex_connect_ready(self, payload: Any) -> None:
        """Publish a completed handshake on the Controller/QML thread."""

        if not isinstance(payload, Mapping):
            self._handle_codex_connect_failed(RuntimeError("Codex 连接响应无效"))
            return
        backend = payload.get("backend")
        thread_id = str(payload.get("thread_id") or "")
        mode = str(payload.get("mode") or "coach")
        token = str(payload.get("token") or "")
        if token and token != self._codex_active_connect_token:
            # A stale handshake must not overwrite a newer connection.
            try:
                # An ``open_thread`` handshake shares the live backend with a
                # newer request.  Never close that shared transport merely
                # because this older token arrived late; only an extra
                # backend created by a superseded initial handshake is safe to
                # close here.
                if (
                    self._codex_loop
                    and backend is not None
                    and backend is not self._codex_backend
                ):
                    asyncio.run_coroutine_threadsafe(backend.close(), self._codex_loop)
            except Exception:
                pass
            return
        if backend is None or not thread_id:
            self._handle_codex_connect_failed(RuntimeError("Codex 连接响应缺少线程信息"))
            return
        if self._shutdown_done:
            try:
                if self._codex_loop:
                    asyncio.run_coroutine_threadsafe(backend.close(), self._codex_loop)
            except Exception:
                pass
            return
        # A stale handshake can complete after a newer connection was
        # selected.  Do not replace the live backend; close the extra one.
        if self._codex_backend is not None and self._codex_backend is not backend:
            try:
                if self._codex_loop:
                    asyncio.run_coroutine_threadsafe(backend.close(), self._codex_loop)
            except Exception:
                pass
            return
        # A genuinely new transport starts with a clean turn-generation
        # namespace.  This keeps the fail-closed rule for id-less protocol
        # adapters useful across reconnects while preserving the fence when
        # only the workflow thread changes on the same live backend.
        fresh_backend = self._codex_backend is not backend
        self._codex_backend_generation += 1
        if fresh_backend:
            self._codex_turn_generation = 0
            self._codex_start_response_turn_id = ""
            self._finish_codex_event_gate()
        self._codex_backend = backend
        self._codex_thread_id = thread_id
        self._codex_threads[mode] = thread_id
        self._codex_thread_mode = mode
        self._ai_status = text("status.codex_connected")
        self.aiStateChanged.emit()
        if self._codex_loop is not None:
            self._codex_loop.call_soon_threadsafe(self._launch_codex_pump, backend)

    @Slot(object)
    def _handle_codex_connect_failed(self, error: Any) -> None:
        keep_existing = False
        if isinstance(error, Mapping):
            token = str(error.get("token") or "")
            if token and token != self._codex_active_connect_token:
                return
            keep_existing = bool(error.get("keep_existing"))
            error = error.get("error") or "Codex 连接失败"
        if keep_existing and self._codex_backend is not None and self._codex_pump_started:
            self._ai_status = text("status.codex_connected")
        else:
            self._ai_status = text("status.ai_offline")
        self.aiStateChanged.emit()
        self._show_error(error if isinstance(error, (BaseException, str)) else str(error))

    @Slot(object)
    def _handle_codex_approval_result(self, payload: Any) -> None:
        """Finalize an approval response on the Controller/QML thread.

        The network future completes on the Codex asyncio thread.  Keeping
        the pending-request mutation here prevents a late response for an
        older request from clearing a newer approval banner.
        """

        if not isinstance(payload, Mapping):
            return
        request_id = str(payload.get("request_id") or "")
        pending = self._codex_pending_approval
        if not pending or str(pending.get("request_id") or "") != request_id:
            return
        error = payload.get("error")
        if error:
            self.codexApprovalFailed.emit(
                {"request_id": request_id, "error": str(error)}
            )
            return
        self._codex_pending_approval = None
        self.codexApprovalResolved.emit(request_id)

    def _launch_codex_pump(self, backend: Any) -> None:
        """Create the transport task in its owning asyncio loop."""

        if backend is not self._codex_backend or self._codex_pump_started:
            return
        self._codex_pump_started = True
        asyncio.create_task(self._pump_codex(backend))

    @Slot(object)
    def _handle_codex_event(self, event: Any) -> None:
        """Route one App Server event on the Controller/QML thread."""

        if self._shutdown_done:
            return
        method = str(getattr(event, "method", "") or "")
        params = event.params if isinstance(getattr(event, "params", None), Mapping) else {}
        event_turn = params.get("turnId") or params.get("turn_id")
        nested_turn = params.get("turn")
        if not event_turn and isinstance(nested_turn, Mapping):
            event_turn = nested_turn.get("id")
        terminal_methods = {"turn/completed", "turn/failed", "turn/aborted", "turn/cancelled"}

        # After Stop/refresh, do not immediately reuse the shared event stream.
        # A pending ``turn/start`` must first resolve so we can bind the real
        # server id; a known id requires an exactly matching terminal event.
        # Nothing else can clear this fence, which prevents a late id-less
        # event from being mistaken for a new turn.
        if self._codex_drain_pending:
            drain_turn = self._codex_drain_turn_id
            if self._codex_drain_waiting_start:
                return
            if method in terminal_methods and drain_turn and event_turn and str(event_turn) == str(drain_turn):
                self._codex_drain_pending = False
                self._codex_drain_turn_id = None
                self._codex_drain_waiting_start = False
                self._codex_drain_token = ""
                self.toast.emit("Codex 已确认停止，可以开始下一次请求。")
            return

        active_kind = (
            "coach" if self._codex_coach_identity is not None
            else "interview" if self._codex_interview_identity is not None
            else ""
        )
        expected_turn = (
            self._codex_coach_turn_id if active_kind == "coach"
            else self._codex_interview_turn_id if active_kind == "interview"
            else None
        )
        # There is no safe owner for an event when neither workflow has an
        # active identity.  In particular, never emit the legacy global delta
        # for an unscoped late event.
        if not active_kind:
            return

        expected_pending = bool(expected_turn and str(expected_turn).startswith("pending:"))
        if method == "turn/started":
            if not expected_turn:
                return
            if not expected_pending:
                # A duplicate start marker must carry the same concrete id.
                if not event_turn or str(event_turn) != str(expected_turn):
                    return
            elif event_turn:
                # Do not let a delayed marker from the previous turn claim
                # this operation before its own ``turn/start`` request has
                # resolved on the Qt thread.
                if (
                    not self._codex_start_ready
                    or not self._codex_start_response_turn_id
                ):
                    self._queue_codex_early_event(event, event_turn)
                    return
                if str(event_turn) != str(self._codex_start_response_turn_id):
                    return
                if active_kind == "coach":
                    self._codex_coach_turn_id = str(event_turn)
                else:
                    self._codex_interview_turn_id = str(event_turn)
                self._codex_turn_id = str(event_turn)
                self._codex_turn_started = True
                self._codex_unscoped_allowed = False
            elif not self._codex_start_ready:
                # Do not accept an old id-less marker that raced ahead of the
                # local ``turn/start`` response.
                return
            else:
                # An id-less start is tolerable only for the very first
                # request on a fresh transport.  After a turn has completed
                # or been replaced, there is no protocol-level way to tell an
                # old id-less marker from the new one; fail closed instead of
                # risking transcript contamination.
                if self._codex_turn_generation > 1:
                    self._invalidate_codex_transport(
                        "Codex 未返回可关联的 turn id"
                    )
                    return
                self._arm_codex_unscoped_turn(active_kind)
            self._codex_diff = ""
            return

        # Once a concrete id is bound, *every* stream event must carry it.  If
        # the server omits ids entirely, only the explicitly announced,
        # unscoped turn below is accepted.  This fail-closed choice is more
        # truthful than appending an indistinguishable old chunk.
        if not expected_turn:
            return
        if not expected_pending:
            if not event_turn or str(event_turn) != str(expected_turn):
                return
        elif event_turn:
            # A provider may send a delta before ``turn/started`` but still
            # include the id.  Bind it only after the local start response;
            # otherwise it could belong to the preceding turn.
            if (
                not self._codex_start_ready
                or not self._codex_start_response_turn_id
            ):
                self._queue_codex_early_event(event, event_turn)
                return
            if str(event_turn) != str(self._codex_start_response_turn_id):
                return
            if active_kind == "coach":
                self._codex_coach_turn_id = str(event_turn)
            else:
                self._codex_interview_turn_id = str(event_turn)
            self._codex_turn_id = str(event_turn)
            expected_pending = False
        elif not self._codex_unscoped_allowed:
            return

        if method == "item/agentMessage/delta":
            delta = params.get("delta", "")
            if isinstance(delta, str):
                if self._codex_coach_identity is not None:
                    self._coach_emit_delta(self._codex_coach_identity, delta)
                elif self._codex_interview_identity is not None:
                    self._codex_interview_buffer += delta
                    self.stateChanged.emit()
        elif method == "item/fileChange/delta":
            delta = params.get("delta", "")
            if isinstance(delta, str):
                # A bounded display buffer only. App Server remains the source
                # of truth and the user must still approve the actual request.
                self._codex_diff = (self._codex_diff + delta)[-100_000:]
        elif method == "turn/completed":
            outcome, detail = _codex_terminal_outcome(params)
            # A transport can stay healthy even when one turn is interrupted
            # or rejected. Keep the connection status truthful while making
            # the individual Coach/Interview result explicitly recoverable.
            self._ai_status = text(
                "status.codex_ready"
                if outcome == "completed"
                else "status.codex_connected"
            )
            self.aiStateChanged.emit()
            if self._codex_coach_identity is not None:
                identity = self._codex_coach_identity
                if outcome == "completed":
                    self._coach_turn_finished(identity, {"cancelled": False})
                elif outcome == "cancelled":
                    self._coach_turn_finished(
                        identity,
                        {
                            "cancelled": True,
                            "error": detail,
                        },
                    )
                else:
                    self._coach_turn_finished(identity, {"error": detail})
            elif self._codex_interview_identity is not None:
                identity = self._codex_interview_identity
                if outcome == "completed":
                    self._finish_codex_interview_assessment(identity)
                else:
                    self._finish_codex_interview_assessment(identity, error=detail)
            self._finish_codex_event_gate()
        elif method in {"turn/failed", "turn/aborted", "turn/cancelled"}:
            if self._codex_coach_identity is not None:
                identity = self._codex_coach_identity
                self._coach_turn_finished(
                    identity,
                    {
                        "error": params.get(
                            "message", "Codex 回答未完成，请检查状态后重试。"
                        )
                    },
                )
            elif self._codex_interview_identity is not None:
                identity = self._codex_interview_identity
                self._finish_codex_interview_assessment(
                    identity,
                    error=str(params.get("message") or "Codex 评分未完成，请检查状态后重试。"),
                )
            self._finish_codex_event_gate()
        elif getattr(event, "requires_approval", False):
            request_id = str(event.request_id)
            approval = {
                "request_id": request_id,
                "action": method,
                "scope": params.get("cwd", "当前仓库"),
                "files": params.get("changes", []),
                "diff": params.get("diff") or self._codex_diff,
                "command": params.get("command", ""),
                "reason": params.get("reason", "未提供原因"),
                "risk": "该操作可能运行命令或修改文件。批准前请核对范围与 Diff。",
                # These fields stay in the Controller so QML cannot approve
                # an arbitrary request id from a stale/forged map.
                "thread_id": self._codex_thread_id or "",
                "turn_id": str(event_turn or ""),
                "workflow": active_kind,
                "backend_generation": self._codex_backend_generation,
            }
            self._codex_pending_approval = approval
            self.codexApproval.emit(approval)

    @Slot(str)
    def connectCodex(self, mode: str = "coach") -> None:
        mode = str(mode or "coach").strip().lower()
        if mode not in {"coach", "teacher", "reviewer", "interviewer", "repository_agent"}:
            self._show_error("不支持的 Codex 工作流模式。")
            return
        if self._codex_connect_future is not None and not self._codex_connect_future.done():
            self.toast.emit("Codex 正在连接，请稍候；也可以继续使用 No-AI。")
            return
        self._codex_connect_generation += 1
        connect_token = f"connect-{self._codex_connect_generation}"
        self._codex_active_connect_token = connect_token
        if self._codex_backend is not None and self._codex_thread_id:
            if self._codex_pump_started:
                if mode in self._codex_threads:
                    if (
                        (self._codex_coach_identity is not None
                         or self._codex_interview_identity is not None)
                        and self._codex_thread_mode != mode
                    ):
                        self.toast.emit("当前 Codex 回答仍在生成，请先等待或停止后再切换工作流。")
                        return
                    self._codex_thread_id = self._codex_threads[mode]
                    self._codex_thread_mode = mode
                    self.aiStateChanged.emit()
                    self.toast.emit("Codex 已连接；已切换到独立的当前工作流线程。")
                    return
                if self._codex_coach_identity is not None or self._codex_interview_identity is not None:
                    self.toast.emit("当前 Codex 回答仍在生成，请先等待或停止后再创建工作流线程。")
                    return
                # Reuse the process, but create a fresh App Server thread with
                # the requested sandbox/approval policy.  Threads are never
                # shared between Coach, Interviewer and repository-agent.
                loop = self._ensure_codex_loop()
                self._ai_status = "Codex 工作流切换中…"
                self.aiStateChanged.emit()

                async def open_thread() -> str:
                    response = await self._codex_backend.start_thread(mode=mode)
                    return str(response["thread"]["id"])

                try:
                    future = asyncio.run_coroutine_threadsafe(open_thread(), loop)
                    self._codex_connect_future = future
                    self.aiStateChanged.emit()
                except Exception as error:
                    self._show_error(error)
                    return

                def opened(value: Any, requested_mode=mode) -> None:
                    try:
                        thread_id = value.result()
                        self._codexConnectReady.emit(
                            {
                                "backend": self._codex_backend,
                                "thread_id": thread_id,
                                "mode": requested_mode,
                                "token": connect_token,
                            }
                        )
                    except Exception as error:
                        self._codexConnectFailed.emit(
                            {
                                "token": connect_token,
                                "error": error,
                                "keep_existing": True,
                            }
                        )
                    finally:
                        if self._codex_connect_future is value:
                            self._codex_connect_future = None

                future.add_done_callback(opened)
                return
            # The event iterator ended between two UI turns.  Treat that
            # backend as dead instead of claiming it is connected forever.
            stale_backend = self._codex_backend
            self._codex_backend = None
            self._codex_backend_generation += 1
            self._codex_thread_id = None
            self._codex_threads = {}
            self._codex_thread_mode = None
            self._ai_status = text("status.ai_offline")
            self.aiStateChanged.emit()
            try:
                if self._codex_loop:
                    asyncio.run_coroutine_threadsafe(
                        stale_backend.close(), self._codex_loop
                    )
            except Exception:
                pass
        try:
            loop = self._ensure_codex_loop()
            self._ai_status = "Codex 连接中…"
            self.aiStateChanged.emit()

            async def connect() -> dict[str, Any]:
                backend = CodexAppServerBackend(
                    self.repo_root,
                    executable=self._codex_executable or None,
                )
                try:
                    await backend.connect()
                    account = await backend.account()
                    if account.get("account") is None:
                        raise RuntimeError("Codex is not signed in")
                    response = await backend.start_thread(mode=mode)
                    thread_id = response["thread"]["id"]
                except Exception:
                    try:
                        await backend.close()
                    except Exception:
                        pass
                    raise
                # Publish only through the queued Qt signal below.  The
                # handshake coroutine itself never mutates QML-facing state.
                return {
                    "backend": backend,
                    "thread_id": thread_id,
                    "mode": mode,
                    "token": connect_token,
                }

            future = asyncio.run_coroutine_threadsafe(connect(), loop)
            self._codex_connect_future = future
            self.aiStateChanged.emit()

            def finished(value) -> None:
                try:
                    caught = value.exception()
                    if caught:
                        self._codexConnectFailed.emit(
                            {"token": connect_token, "error": caught}
                        )
                    else:
                        self._codexConnectReady.emit(value.result())
                except Exception as callback_error:
                    self._codexConnectFailed.emit(
                        {"token": connect_token, "error": callback_error}
                    )
                finally:
                    if self._codex_connect_future is value:
                        self._codex_connect_future = None

            future.add_done_callback(finished)
        except Exception as error:
            self._ai_status = text("status.ai_offline")
            self.aiStateChanged.emit()
            self._show_error(error)

    @Slot(str)
    def sendCodexMessage(self, message: str) -> None:
        if self._codex_coach_identity is not None or self._codex_interview_identity is not None:
            self.toast.emit("已有 Codex 回答正在生成，请先等待或停止。")
            return
        if self._codex_drain_pending:
            self.toast.emit("Codex 正在确认上一次停止，请稍候后再发送。")
            return
        if self._codex_loop is None or self._codex_backend is None or not self._codex_thread_id:
            self.toast.emit("请先连接 Codex；也可以继续使用无需 AI 的本地功能。")
            return
        future = asyncio.run_coroutine_threadsafe(
            self._codex_backend.start_turn(self._codex_thread_id, message),
            self._codex_loop,
        )
        future.add_done_callback(
            lambda value: self._show_error(value.exception())
            if value.exception()
            else None
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
        session = self._coach_session()
        if session is None:
            if not self.createCoachSession(
                mode, "codex", self._active_problem_id(), ""
            ):
                return
            session = self._coach_session()
        elif session.get("mode") != mode and session.get("messages"):
            self._set_coach_error("会话模式已锁定，请新建会话后切换。")
            return
        if not self._coach_provider_matches(session, "codex"):
            self._set_coach_error(
                "本地会话已有消息，不能切换到 Codex；请新建会话后再切换。"
            )
            return
        self._start_coach_turn(
            message=message,
            provider_kind="codex",
            help_level=help_level,
            include_submission=include_submission,
            include_test_output=include_test_output,
        )

    def _release_codex_interview_turn(self, operation_id: str) -> None:
        self._background_operations.discard(operation_id)
        self._set_busy(bool(self._background_operations))
        if self._codex_interview_operation_id == operation_id:
            self._codex_interview_operation_id = ""
            self._codex_interview_turn_id = None
            self._codex_interview_message_id = ""

    def _finish_codex_interview_assessment(
        self,
        identity: tuple[str, str, str, str, str],
        *,
        error: str = "",
    ) -> None:
        """Validate one Codex scorecard before writing interview evidence."""

        profile_id, interview_id, question_id, operation_id, provider_kind = identity
        if self._codex_interview_operation_id != operation_id:
            return
        try:
            if (
                error
                or self._profile_id != profile_id
                or self._interview.get("interview_id") != interview_id
                or (self._interview.get("question") or {}).get("question_id") != question_id
            ):
                raise RuntimeError(error or "当前面试问题已经切换，已丢弃旧的 Codex 评分。")
            question = self._interview.get("question") or {}
            result = _decode_ai_assessment(
                self._codex_interview_buffer,
                set(question.get("rubric", {}).get("dimensions", {})),
                set(question.get("rubric", {}).get("fatal_issues", [])),
            )
            latest = self.service.interview_session(profile_id, interview_id)
            if latest.get("status") != "active" or question_id in latest.get("assessments", {}):
                raise RuntimeError("当前问题已经评分或面试已经结束，未重复写入 Codex 结果。")
            if result["follow_up"]:
                self._pending_ai_assessment = {
                    **result,
                    "profile_id": profile_id,
                    "interview_id": interview_id,
                    "question_id": question_id,
                    "provider_kind": provider_kind,
                    "operation_id": operation_id,
                }
                self._interview["pending_followup"] = result["follow_up"]
                self._interview["ai_assessment_state"] = "followup"
            else:
                self.service.score_interview(
                    profile_id,
                    interview_id,
                    question_id,
                    result["scores"],
                    evidence=result["evidence"],
                    source="ai",
                    confidence=result["confidence"],
                    fatal_issues=result["fatal_issues"],
                )
                self._interview["ai_assessment_state"] = "complete"
                self._load_interview(interview_id)
            self._interview["ai_error"] = ""
        except Exception as caught:
            self._interview["ai_assessment_state"] = "error"
            self._interview["ai_error"] = friendly_error(caught)
            self._show_error(caught)
        finally:
            self._codex_interview_buffer = ""
            self._codex_interview_identity = None
            self._release_codex_interview_turn(operation_id)
            self.stateChanged.emit()

    @Slot(str, bool, result=bool)
    def sendCodexInterviewAnswer(
        self, answer: str, include_materials: bool = True
    ) -> bool:
        """Request a strict, evidence-backed Codex scorecard.

        This path is intentionally separate from the generic Coach transcript:
        prose or an unvalidated response can never be mistaken for an
        interview assessment.
        """

        if not self._interview.get("interview_id"):
            self._show_error("请先开始一场模拟面试。")
            return False
        if self._codex_interview_identity is not None or self._codex_interview_operation_id:
            self._show_error("Codex 评分仍在生成，请等待完成或结束本次请求。")
            return False
        if self._codex_coach_identity is not None:
            self._show_error("Codex Coach 回答仍在生成，请先等待或停止后再请求面试评分。")
            return False
        if self._codex_thread_mode not in {None, "interviewer"}:
            self._show_error(
                "当前 Codex 连接属于其他工作流；请先连接“面试官模式”后再评分。"
            )
            return False
        if self._codex_drain_pending:
            self._show_error("Codex 正在确认上一次停止，请收到确认后再请求面试评分。")
            return False
        question = self._interview.get("question") or {}
        if self._interview.get("status") != "active" or self._interview.get("expired"):
            self._show_error("当前面试已暂停、超时或结束，不能请求 Codex 评分。请先恢复计时或开始新场次。")
            return False
        if question.get("kind") == "coding":
            self._show_error("coding 面试只接受本地 Grader 证据，不能请求文本评分。")
            return False
        if self._interview.get("answer_corrupted") or not str(self._interview.get("answer_text") or "").strip():
            self._show_error("请先提交并锁定当前回答，再请求 Codex 评估。")
            return False
        if self._codex_backend is None or not self._codex_thread_id or self._codex_loop is None:
            self._show_error("Codex 尚未连接。请先连接 Codex，或改用人工评分；本地训练仍可继续。")
            return False
        try:
            preview = build_role_interview_context_preview(
                self.repo_root,
                self._profile_id,
                self._interview["interview_id"],
                candidate_answer=str(self._interview.get("answer_text") or answer),
                include_materials=include_materials,
            )
        except Exception as caught:
            self._show_error(caught)
            return False
        dimensions = set(question.get("rubric", {}).get("dimensions", {}))
        fatal_issues = set(question.get("rubric", {}).get("fatal_issues", []))
        operation_id = uuid4().hex
        message_id = f"msg-{uuid4().hex}"
        identity = (
            self._profile_id,
            self._interview["interview_id"],
            str(question.get("question_id") or ""),
            operation_id,
            "codex",
        )
        self._codex_interview_identity = identity
        self._begin_codex_turn("interview", operation_id)
        self._codex_interview_buffer = ""
        self._codex_interview_dimensions = dimensions
        self._codex_interview_fatal_issues = fatal_issues
        self._codex_interview_operation_id = operation_id
        self._codex_interview_message_id = message_id
        self._interview["ai_assessment_state"] = "streaming"
        self._interview["ai_error"] = ""
        self._background_operations.add(operation_id)
        self._set_busy(True)
        self.stateChanged.emit()
        instruction = (
            "Return JSON only with exactly these fields: scores (one integer 1-5 for "
            f"each of {sorted(dimensions)}), evidence (20-4000 characters citing the "
            "locked candidate answer), confidence (low|medium|high), fatal_issues "
            f"(only from {sorted(fatal_issues)}), and follow_up (one concise adaptive "
            "question or an empty string). Do not invent career facts, do not modify "
            "the answer, and do not claim Practice mastery."
        )
        prompt = preview.selected_text + "\n\n## Frozen scorecard contract\n" + instruction
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._codex_backend.start_turn(self._codex_thread_id, prompt),
                self._codex_loop,
            )
        except Exception as caught:
            self._codex_interview_identity = None
            self._finish_codex_interview_assessment(identity, error=str(caught))
            return False

        def on_started(value, token=identity) -> None:
            try:
                caught = value.exception()
                if caught:
                    self._codexTurnStarted.emit(
                        {"kind": "interview", "identity": token, "error": str(caught)}
                    )
                    return
                response = value.result() or {}
                turn = response.get("turn") if isinstance(response, Mapping) else None
                turn_id = (turn or {}).get("id") if isinstance(turn, Mapping) else None
                self._codexTurnStarted.emit(
                    {"kind": "interview", "identity": token, "turn_id": turn_id}
                )
            except Exception as caught:
                self._codexTurnStarted.emit(
                    {"kind": "interview", "identity": token, "error": str(caught)}
                )

        future.add_done_callback(on_started)
        return True

    @Slot(str, str)
    def resolveCodexApproval(self, request_id: str, decision: str) -> None:
        request_id = str(request_id or "")
        pending = self._codex_pending_approval
        if not pending or str(pending.get("request_id") or "") != request_id:
            self.codexApprovalFailed.emit(
                {
                    "request_id": request_id,
                    "error": "审批请求已过期或不属于当前 Codex 操作；请等待新的请求。",
                }
            )
            return
        if pending.get("backend_generation") != self._codex_backend_generation or (
            pending.get("thread_id") and pending.get("thread_id") != self._codex_thread_id
        ):
            self.codexApprovalFailed.emit(
                {
                    "request_id": request_id,
                    "error": "Codex 工作流已变化，未发送这次审批；请重新检查新的 Diff。",
                }
            )
            return
        if decision not in {"accept", "acceptForSession", "decline", "cancel"}:
            self.codexApprovalFailed.emit(
                {"request_id": request_id, "error": "不支持的审批决定。"}
            )
            return
        if self._codex_loop is None or self._codex_backend is None:
            self.codexApprovalFailed.emit(
                {
                    "request_id": request_id,
                    "error": "Codex 尚未连接；审批请求仍保持待处理。",
                }
            )
            return
        parsed: int | str = int(request_id) if request_id.isdigit() else request_id
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._codex_backend.resolve_approval(parsed, decision), self._codex_loop
            )
        except Exception as error:
            self.codexApprovalFailed.emit(
                {"request_id": str(request_id), "error": str(error)}
            )
            return

        def finished(value: Any) -> None:
            try:
                error = value.exception()
                if error:
                    self.codexApprovalFailed.emit(
                        {"request_id": request_id, "error": str(error)}
                    )
                else:
                    self._codexApprovalResult.emit({"request_id": request_id})
            except Exception as callback_error:
                self._codexApprovalResult.emit(
                    {"request_id": request_id, "error": str(callback_error)}
                )

        future.add_done_callback(finished)

    @Slot()
    def cancelCodex(self) -> None:
        turn_id = self._codex_coach_turn_id or self._codex_interview_turn_id or self._codex_turn_id
        if not turn_id or str(turn_id).startswith("pending:"):
            # ``pending:<operation>`` is a local fence, never a server turn
            # identifier.  The turn-start callback will interrupt a concrete
            # id if one is eventually returned.
            return
        if (
            self._codex_loop
            and self._codex_backend
            and self._codex_thread_id
        ):
            asyncio.run_coroutine_threadsafe(
                self._codex_backend.interrupt(
                    self._codex_thread_id,
                    turn_id,
                ),
                self._codex_loop,
            )

    @Slot(str)
    def setTheme(self, value: str) -> None:
        if value in {"system", "light", "dark"}:
            self._theme = value
            if not self._demo_mode:
                self._settings.setValue("theme", value)
            self.stateChanged.emit()

    @Slot(float)
    def setFontScale(self, value: float) -> None:
        self._font_scale = max(0.85, min(1.4, value))
        if not self._demo_mode:
            self._settings.setValue("fontScale", self._font_scale)
        self.stateChanged.emit()

    @Slot()
    def refreshCodexAvailability(self) -> None:
        """Probe Codex off the GUI thread and cache the visible status."""

        if self._demo_mode:
            # Synthetic pages must not inspect PATH or a user's local binary.
            self._codex_available = False
            return
        if self._codex_probe_running or self._shutdown_done:
            return
        self._codex_probe_running = True
        configured = self._codex_executable or None
        worker = Worker(lambda: discover_codex_executable(configured))
        self._workers.add(worker)

        def finish(value: object) -> None:
            self._workers.discard(worker)
            self._codex_probe_running = False
            self._codex_available = value is not None
            self.aiStateChanged.emit()

        def fail(_: str) -> None:
            self._workers.discard(worker)
            self._codex_probe_running = False
            self._codex_available = False
            self.aiStateChanged.emit()

        worker.signals.completed.connect(finish)
        worker.signals.failed.connect(fail)
        self._thread_pool.start(worker)

    @Slot(str)
    def setCodexExecutable(self, value: str) -> None:
        if self._demo_mode:
            self.toast.emit("合成演示不会保存或探测本机 Codex 路径。")
            return
        candidate = QUrl(value).toLocalFile() if value.startswith("file:") else value
        path = Path(candidate).expanduser()
        resolved = discover_codex_executable(path)
        if resolved is None:
            self.toast.emit(text("error.codex_missing"))
            return
        self._codex_executable = resolved
        self._codex_available = True
        self._settings.setValue("codexExecutable", self._codex_executable)
        self.aiStateChanged.emit()
        self.stateChanged.emit()
        self.toast.emit("Codex 可执行文件位置已保存。")

    @Slot()
    def clearCodexExecutable(self) -> None:
        if self._demo_mode:
            self._codex_executable = ""
            self._codex_available = False
            self.aiStateChanged.emit()
            self.stateChanged.emit()
            return
        self._codex_executable = ""
        self._codex_available = False
        self._settings.remove("codexExecutable")
        self.aiStateChanged.emit()
        self.stateChanged.emit()
        self.refreshCodexAvailability()

    @Slot()
    def openDataDirectory(self) -> None:
        if self._demo_mode:
            self.toast.emit("合成演示不会打开维护者的真实数据目录。")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.repo_root)))

    @Slot()
    def openLogDirectory(self) -> None:
        if self._demo_mode:
            self.toast.emit("合成演示不会打开维护者的真实日志目录。")
            return
        self._log_root.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._log_root)))

    @Slot()
    def dismissLegacyMigration(self) -> None:
        if self._demo_mode:
            return
        self._legacy_migration_dismissed = True
        self.stateChanged.emit()

    @Slot()
    def migrateLegacyData(self) -> None:
        if self._demo_mode:
            self.toast.emit("合成演示不会迁移维护者的真实数据。")
            return
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
