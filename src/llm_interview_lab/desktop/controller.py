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

from ..ai.codex_backend import CodexAppServerBackend, CodexEvent
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
        self._ai_status = "Disconnected"
        self._workers: set[Worker] = set()
        self._thread_pool = QThreadPool.globalInstance()
        self._settings = QSettings("ComistryMo", "LLMInterviewLab")
        self._theme = str(self._settings.value("theme", "system"))
        self._font_scale = float(self._settings.value("fontScale", 1.0))
        self._codex_loop: asyncio.AbstractEventLoop | None = None
        self._codex_thread: threading.Thread | None = None
        self._codex_backend: CodexAppServerBackend | None = None
        self._codex_thread_id: str | None = None
        self._codex_turn_id: str | None = None
        self._codex_diff = ""
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
        self._test_output = "Ready — public tests have not run yet."
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
            {"connection_id": "ollama-local", "provider_id": "ollama", "display_name": "Local Ollama", "model": "qwen", "status": "Not tested"},
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

    @Property(str, notify=stateChanged)
    def profileId(self) -> str:
        return self._profile_id

    @Property(bool, notify=stateChanged)
    def onboardingRequired(self) -> bool:
        return self._onboarding

    @Property("QVariantList", notify=stateChanged)
    def roles(self) -> list[dict[str, Any]]:
        return self.service.role_cards()

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
        return CodexAppServerBackend(self.repo_root).available()

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
            self.toast.emit(message)

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
            self._problems = self.service.problem_cards(self._profile_id)
            current = self.service.current_submission(self._profile_id)
            if current:
                self._current_task = self.service.problem_view(current["problem_id"])
                self._submission = current["text"]
            self._connections = [
                {**config.__dict__, "status": "Saved"}
                for config in list_connections(self.repo_root, self._profile_id)
            ]
            self._materials = self.service.material_cards(self._profile_id)
            self._onboarding = False
        except Exception as error:
            self.toast.emit(str(error))
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
            self.toast.emit(str(error))

    @Slot(str, str, str, bool)
    def addMaterial(
        self, source_url: str, kind: str, title: str, ai_access: bool
    ) -> None:
        if self._profile_id == "demo":
            self.toast.emit("Demo materials are synthetic and read-only")
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
            self.toast.emit("Material copied into the ignored local Profile")
        except Exception as error:
            self.toast.emit(str(error))

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
            self._test_output = "Ready — run public tests when your attempt is complete."
            self._page = "exercise"
            self.stateChanged.emit()
            self.pageChanged.emit()
        except Exception as error:
            self.toast.emit(str(error))

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
            self.toast.emit("Saved locally")
        except Exception as error:
            self.toast.emit(str(error))

    @Slot()
    def runTests(self) -> None:
        if not self._current_task:
            return
        if self._profile_id == "demo":
            self._test_output = "5 passed in 0.18s\n\nPublic tests: PASS · Mastery: NOT YET"
            self.stateChanged.emit()
            return
        problem_id = self._current_task["problem_id"]

        def complete(result) -> None:
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"Public tests: {result.status.upper()} · Mastery: NOT YET"
            )
            self.stateChanged.emit()

        self._background(
            lambda: self.service.run_practice_tests(self._profile_id, problem_id),
            complete,
        )

    @Slot()
    def submitCurrent(self) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("Demo submission is not recorded")
            return
        try:
            result = self.service.submit_practice(
                self._profile_id, self._current_task["problem_id"]
            )
            self.toast.emit(
                "Implemented; contract and oral review remain"
                if result["implemented"]
                else "Submission recorded; current tests are not passing"
            )
            self.refresh()
        except Exception as error:
            self.toast.emit(str(error))

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
            self.toast.emit("A real active Practice attempt is required")
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
                f"Review recorded: {result.status}; mastery is determined by the lifecycle"
            )
            self.refresh()
        except Exception as error:
            self.toast.emit(str(error))

    @Slot(str)
    def startRetentionStage(self, stage: str) -> None:
        if not self._current_task or self._profile_id == "demo":
            self.toast.emit("A real reviewed Practice problem is required")
            return
        try:
            problem_id = self._current_task["problem_id"]
            result = self.service.start_retention(self._profile_id, problem_id, stage)
            current = self.service.current_submission(self._profile_id)
            if current is None:
                raise RuntimeError("retention attempt was not created")
            self._submission = current["text"]
            self._test_output = (
                f"{stage.upper()} attempt {result['attempt_id']} is independent; "
                "the previous submission was not copied."
            )
            self.stateChanged.emit()
            self.toast.emit(f"Started verified {stage.upper()} retention attempt")
        except Exception as error:
            self.toast.emit(str(error))

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
            self.toast.emit(str(error))

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
            self.toast.emit(str(error))

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
            self.toast.emit(str(error))

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
            self.toast.emit("Interview answer saved inside this local session")
        except Exception as error:
            self.toast.emit(str(error))

    @Slot(str)
    def runInterviewCoding(self, text: str) -> None:
        if self._profile_id == "demo":
            self._test_output = "4 passed in 0.16s\n\nCoding evidence: PASS"
            self.stateChanged.emit()
            return
        try:
            self.service.save_interview_coding_submission(
                self._profile_id, self._interview["interview_id"], text
            )
        except Exception as error:
            self.toast.emit(str(error))
            return

        def complete(result) -> None:
            self._test_output = (
                (result.output + "\n\n" if result.output else "")
                + f"Coding evidence: {result.status.upper()}"
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
            self.toast.emit("Synthetic coding round recorded")
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
            self.toast.emit(str(error))

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
            self.toast.emit("Manual rubric scores are invalid")
            return
        self._record_manual_interview_assessment(answer, scores, evidence)

    def _record_manual_interview_assessment(
        self, answer: str, scores: Any, evidence: str
    ) -> None:
        if self._profile_id == "demo":
            self.toast.emit("Demo answer recorded locally for this preview")
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
            self.toast.emit(str(error))

    @Slot(str, str, bool)
    def assessInterviewWithProvider(
        self, answer: str, connection_id: str, include_materials: bool = True
    ) -> None:
        question = self._interview.get("question")
        if not question or question.get("kind") == "coding":
            return
        if self._profile_id == "demo":
            self.toast.emit(
                "Demo AI assessment: evidence required; Practice mastery unchanged"
            )
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
                self.toast.emit(str(error))

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
            self.toast.emit(str(error))

    @Slot()
    def finishInterview(self) -> None:
        if self._profile_id == "demo":
            self.toast.emit("Demo report: 76/100 · Practice mastery unchanged")
            return
        try:
            session = self.service.finish_interview(
                self._profile_id,
                self._interview["interview_id"],
                summary="Local structured interview completed.",
                confirm_incomplete=True,
            )
            self._interview = session
            self.stateChanged.emit()
        except Exception as error:
            self.toast.emit(str(error))

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
            self.toast.emit("Connection saved; API key is in the system keyring")
        except (ConnectionConfigError, CredentialError) as error:
            self.toast.emit(str(error))

    @Slot(str)
    def deleteConnection(self, connection_id: str) -> None:
        try:
            delete_connection(self.repo_root, self._profile_id, connection_id)
            self.refresh()
        except Exception as error:
            self.toast.emit(str(error))

    @Slot(str)
    def testConnection(self, connection_id: str) -> None:
        if self._profile_id == "demo":
            self.toast.emit("Synthetic demo connection check completed")
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
                    item["status"] = "Connected" if result.ok else "Failed"
            self.stateChanged.emit()
            self.toast.emit(result.message)

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
                    {"id": "policy", "label": "AI policy", "selected": True, "sensitive": False},
                    {"id": "task", "label": "Current public task", "selected": True, "sensitive": False},
                    {"id": "submission", "label": "Selected current submission", "selected": include_submission, "sensitive": True},
                    {"id": "test", "label": "Latest public test summary", "selected": include_test_output, "sensitive": False},
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
            self.toast.emit(str(error))
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
            self.toast.emit(str(error))
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

        self._background(operation, lambda _: self.toast.emit("AI response completed"))

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
                self._ai_status = "Codex ready"
                self.aiStateChanged.emit()
            elif event.requires_approval:
                params = event.params
                self.codexApproval.emit(
                    {
                        "request_id": str(event.request_id),
                        "action": event.method,
                        "scope": params.get("cwd", "current repository"),
                        "files": params.get("changes", []),
                        "diff": params.get("diff") or self._codex_diff,
                        "command": params.get("command", ""),
                        "reason": params.get("reason", "No reason supplied"),
                        "risk": "This may run a command or change files. Review before approval.",
                    }
                )

    @Slot(str)
    def connectCodex(self, mode: str = "coach") -> None:
        try:
            loop = self._ensure_codex_loop()

            async def connect() -> None:
                self._codex_backend = CodexAppServerBackend(self.repo_root)
                await self._codex_backend.connect()
                account = await self._codex_backend.account()
                if account.get("account") is None:
                    raise RuntimeError("Codex is not signed in")
                response = await self._codex_backend.start_thread(mode=mode)
                self._codex_thread_id = response["thread"]["id"]
                self._ai_status = "Codex connected"
                self.aiStateChanged.emit()
                asyncio.create_task(self._pump_codex())

            future = asyncio.run_coroutine_threadsafe(connect(), loop)
            future.add_done_callback(
                lambda value: self.toast.emit(str(value.exception())) if value.exception() else None
            )
        except Exception as error:
            self.toast.emit(str(error))

    @Slot(str)
    def sendCodexMessage(self, message: str) -> None:
        if self._codex_loop is None or self._codex_backend is None or not self._codex_thread_id:
            self.toast.emit("Connect Codex first")
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
            self.toast.emit(str(error))

    @Slot(str, bool)
    def sendCodexInterviewAnswer(
        self, answer: str, include_materials: bool = True
    ) -> None:
        if not self._interview.get("interview_id"):
            self.toast.emit("Start an interview first")
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
            self.toast.emit(str(error))

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

    @Slot()
    def shutdown(self) -> None:
        if self._codex_loop and self._codex_backend:
            future = asyncio.run_coroutine_threadsafe(
                self._codex_backend.close(), self._codex_loop
            )
            try:
                future.result(timeout=4)
            except Exception:
                pass
        if self._codex_loop:
            self._codex_loop.call_soon_threadsafe(self._codex_loop.stop)
