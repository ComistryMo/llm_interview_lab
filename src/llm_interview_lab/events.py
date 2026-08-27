"""Append-only profile history and a deterministic physical-order reducer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
TEST_STATUSES = frozenset({"passed", "failed", "timed_out", "collection_error", "import_error", "internal_error"})
PROBLEM_STATUSES = ("not_started", "in_progress", "implemented", "reviewed", "retained_d2", "retained_d7", "mastered")


class EventError(RuntimeError):
    """Raised when profile history is malformed or cannot be appended."""


@dataclass
class AttemptState:
    problem_id: str
    attempt_id: str
    submission_relpath: str | None = None
    retention_stage: str | None = None
    retention_verified: bool = False
    implemented: bool = False
    reviewed: bool = False
    revision_required: bool = False
    last_public_test: dict[str, Any] | None = None
    implemented_sha256: str | None = None


@dataclass
class WorkspaceState:
    profile_id: str | None = None
    current_problem_id: str | None = None
    current_attempt_id: str | None = None
    assistance_level: str | None = None
    attempts: dict[tuple[str, str], AttemptState] = field(default_factory=dict)
    reviewed_at: dict[str, datetime] = field(default_factory=dict)
    retained_d2: set[str] = field(default_factory=set)
    retained_d7: set[str] = field(default_factory=set)
    mastered: set[str] = field(default_factory=set)

    def attempt(self, problem_id: str, attempt_id: str) -> AttemptState | None:
        return self.attempts.get((problem_id, attempt_id))

    def attempts_for(self, problem_id: str) -> tuple[AttemptState, ...]:
        return tuple(attempt for (candidate, _), attempt in self.attempts.items() if candidate == problem_id)

    def latest_attempt(self, problem_id: str) -> AttemptState | None:
        attempts = self.attempts_for(problem_id)
        return attempts[-1] if attempts else None

    def current_attempt(self) -> AttemptState | None:
        if self.current_problem_id is None or self.current_attempt_id is None:
            return None
        return self.attempt(self.current_problem_id, self.current_attempt_id)

    def problem_implemented(self, problem_id: str) -> bool:
        return any(attempt.implemented and attempt.retention_stage is None for attempt in self.attempts_for(problem_id))

    def problem_reviewed(self, problem_id: str) -> bool:
        return problem_id in self.reviewed_at

    def problem_status(self, problem_id: str) -> str:
        if problem_id in self.mastered:
            return "mastered"
        if problem_id in self.retained_d7:
            return "retained_d7"
        if problem_id in self.retained_d2:
            return "retained_d2"
        if self.problem_reviewed(problem_id):
            return "reviewed"
        if self.problem_implemented(problem_id):
            return "implemented"
        if self.attempts_for(problem_id):
            return "in_progress"
        return "not_started"


@dataclass(frozen=True)
class AppendResult:
    event: dict[str, Any]
    appended: bool


@dataclass(frozen=True)
class MistakeFailure:
    """One historical failure, retained even after later evidence recovers it."""

    event_id: str
    problem_id: str
    attempt_id: str
    failed_at: datetime
    failure_kind: str
    recovered: bool


@dataclass(frozen=True)
class MistakeSummary:
    """A problem-level view derived from events without becoming a new fact source."""

    problem_id: str
    failure_count: int
    last_failed_at: datetime
    last_failed_sequence: int
    last_failure_kind: str
    current_evidence_recovered: bool
    failure_history: tuple[MistakeFailure, ...]


@dataclass
class _PendingMistakeFailure:
    event_id: str
    problem_id: str
    attempt_id: str
    failed_at: datetime
    sequence: int
    failure_kind: str
    evidence_channel: str
    recovered: bool = False


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_schema(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EventError("workspace event schema cannot be read") from error
    if not isinstance(data, dict):
        raise EventError("workspace event schema must be a JSON object")
    return data


def _contains_absolute_path(value: Any) -> bool:
    if isinstance(value, str):
        return value.startswith(("/", "\\\\")) or WINDOWS_ABSOLUTE_RE.match(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_absolute_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_absolute_path(item) for item in value)
    return False


def _nonnegative_int(payload: Mapping[str, Any], name: str) -> None:
    if type(payload.get(name)) is not int or payload[name] < 0:
        raise EventError(f"{name} must be a non-negative integer")


def _digest(payload: Mapping[str, Any], event_type: str) -> None:
    value = payload.get("submission_sha256")
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise EventError(f"{event_type} requires submission_sha256")


def _validate_contract(event: Mapping[str, Any]) -> None:
    event_type = event.get("event_type")
    problem_id = event.get("problem_id")
    attempt_id = event.get("attempt_id")
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        raise EventError("event payload must be an object")
    if _contains_absolute_path(payload):
        raise EventError("event payload must not contain absolute paths")
    if event_type == "profile_created":
        if problem_id is not None or attempt_id is not None:
            raise EventError("profile_created cannot identify a problem attempt")
        return
    if problem_id is None or attempt_id is None:
        raise EventError(f"{event_type} requires problem_id and attempt_id")
    if event_type == "task_started":
        stage = payload.get("retention_stage")
        if stage not in {None, "d2", "d7"}:
            raise EventError("task_started retention_stage must be d2 or d7")
    if event_type == "public_tests_run":
        required = {"submission_sha256", "exit_code", "status", "passed", "failed", "duration_ms"}
        missing = sorted(required - set(payload))
        if missing:
            raise EventError(f"public_tests_run payload missing: {', '.join(missing)}")
        _digest(payload, event_type)
        for name in ("exit_code", "passed", "failed", "duration_ms"):
            _nonnegative_int(payload, name)
        if payload["status"] not in TEST_STATUSES:
            raise EventError("public test status is invalid")
    if event_type in {"submission_created", "task_implemented", "retention_d2_passed", "retention_d7_passed", "task_mastered"}:
        _digest(payload, str(event_type))
    if event_type == "review_completed":
        if payload.get("contract_status") not in {"passed", "failed"} or payload.get("oral_status") not in {"passed", "failed"}:
            raise EventError("review statuses must be passed or failed")
        for field_name in ("code_explanation", "complexity", "boundary_conditions"):
            if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
                raise EventError(f"review requires {field_name}")


def validate_event(event: Mapping[str, Any], schema_path: Path) -> None:
    validator = Draft202012Validator(_load_schema(schema_path), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(event), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise EventError(f"invalid event at {location}: {errors[0].message}")
    _validate_contract(event)


def read_events(path: Path, schema_path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise EventError("events.jsonl cannot be read") from error
    events: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise EventError(f"events.jsonl contains blank line {number}")
        try:
            event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as error:
            raise EventError(f"invalid JSON on events line {number}") from error
        if not isinstance(event, dict):
            raise EventError(f"event line {number} must be an object")
        validate_event(event, schema_path)
        if event["event_id"] in seen_ids:
            raise EventError(f"duplicate event ID: {event['event_id']}")
        seen_ids.add(event["event_id"])
        events.append(event)
    return events


def reduce_events(events: Iterable[Mapping[str, Any]]) -> WorkspaceState:
    state = WorkspaceState()
    for event in events:
        profile_id = str(event["profile_id"])
        if state.profile_id is not None and state.profile_id != profile_id:
            raise EventError("events.jsonl mixes multiple profile IDs")
        state.profile_id = profile_id
        event_type = str(event["event_type"])
        if event_type == "profile_created":
            continue
        problem_id = str(event["problem_id"])
        attempt_id = str(event["attempt_id"])
        key = (problem_id, attempt_id)
        payload = dict(event["payload"])
        if event_type in {"task_started", "legacy_import"}:
            if key in state.attempts:
                raise EventError(f"attempt started more than once: {problem_id}/{attempt_id}")
            state.attempts[key] = AttemptState(
                problem_id, attempt_id, payload.get("submission_relpath"), payload.get("retention_stage"),
                bool(payload.get("retention_verified", False)),
                revision_required=bool(payload.get("revision_required", False)),
            )
            state.current_problem_id, state.current_attempt_id = problem_id, attempt_id
            if isinstance(payload.get("assistance_level"), str):
                state.assistance_level = payload["assistance_level"]
            continue
        attempt = state.attempts.get(key)
        if attempt is None:
            raise EventError(f"event references unknown attempt: {problem_id}/{attempt_id}")
        if event_type == "public_tests_run":
            attempt.last_public_test = payload
        elif event_type == "task_implemented":
            attempt.implemented = True
            attempt.implemented_sha256 = payload["submission_sha256"]
            attempt.revision_required = False
        elif event_type == "review_completed" and payload["contract_status"] == payload["oral_status"] == "passed":
            attempt.reviewed = True
            if attempt.retention_stage is None:
                state.reviewed_at[problem_id] = datetime.fromisoformat(str(event["timestamp"]))
        elif event_type == "retention_d2_passed":
            state.retained_d2.add(problem_id)
        elif event_type == "retention_d7_passed":
            state.retained_d7.add(problem_id)
        elif event_type == "task_mastered":
            state.mastered.add(problem_id)
    return state


def _mistake_timestamp(event: Mapping[str, Any]) -> datetime:
    try:
        value = datetime.fromisoformat(str(event["timestamp"]))
    except (KeyError, TypeError, ValueError) as error:
        raise EventError("mistake history contains an invalid timestamp") from error
    if value.tzinfo is None or value.utcoffset() is None:
        raise EventError("mistake history timestamp must include a timezone")
    return value


def _review_failure_kind(payload: Mapping[str, Any]) -> str | None:
    failed = [
        name
        for name, field_name in (("contract", "contract_status"), ("oral", "oral_status"))
        if payload.get(field_name) == "failed"
    ]
    return f"review_{'_and_'.join(failed)}_failed" if failed else None


def summarize_mistakes(events: Iterable[Mapping[str, Any]]) -> tuple[MistakeSummary, ...]:
    """Reduce failure evidence in physical event order.

    A later passing public test recovers public-test and generic task failures for the
    same attempt. A passing review similarly recovers review and generic task failures.
    Mastery recovers every historical failure for that problem. Recovered failures stay
    in ``failure_history`` so this projection never erases the learner's error history.
    """

    history = tuple(events)
    reduce_events(history)  # Reuse canonical profile/attempt sequence validation.
    failures_by_problem: dict[str, list[_PendingMistakeFailure]] = {}
    pending: dict[tuple[str, str, str], list[_PendingMistakeFailure]] = {}

    def record(
        event: Mapping[str, Any],
        failure_kind: str,
        evidence_channel: str,
        sequence: int,
    ) -> None:
        problem_id = str(event["problem_id"])
        attempt_id = str(event["attempt_id"])
        failure = _PendingMistakeFailure(
            event_id=str(event["event_id"]),
            problem_id=problem_id,
            attempt_id=attempt_id,
            failed_at=_mistake_timestamp(event),
            sequence=sequence,
            failure_kind=failure_kind,
            evidence_channel=evidence_channel,
        )
        failures_by_problem.setdefault(problem_id, []).append(failure)
        pending.setdefault((problem_id, attempt_id, evidence_channel), []).append(failure)

    def recover(problem_id: str, attempt_id: str, *channels: str) -> None:
        for channel in channels:
            for failure in pending.pop((problem_id, attempt_id, channel), []):
                failure.recovered = True

    for sequence, event in enumerate(history):
        event_type = str(event["event_type"])
        if event_type == "profile_created":
            continue
        problem_id = str(event["problem_id"])
        attempt_id = str(event["attempt_id"])
        payload = event["payload"]
        if event_type == "public_tests_run":
            status = str(payload["status"])
            if status == "passed":
                recover(problem_id, attempt_id, "public_tests", "task")
            elif status in {"failed", "timed_out", "import_error"}:
                record(
                    event,
                    f"public_tests_{status}",
                    "public_tests",
                    sequence,
                )
        elif event_type == "review_completed":
            failure_kind = _review_failure_kind(payload)
            if failure_kind is None:
                recover(problem_id, attempt_id, "review", "task")
            else:
                record(event, failure_kind, "review", sequence)
        elif event_type == "task_failed":
            record(event, "task_failed", "task", sequence)
        elif event_type == "task_implemented":
            recover(problem_id, attempt_id, "task")
        elif event_type == "task_mastered":
            for failure in failures_by_problem.get(problem_id, []):
                failure.recovered = True
            for key in tuple(pending):
                if key[0] == problem_id:
                    pending.pop(key)

    summaries: list[MistakeSummary] = []
    for problem_id, failures in failures_by_problem.items():
        history_view = tuple(
            MistakeFailure(
                event_id=failure.event_id,
                problem_id=failure.problem_id,
                attempt_id=failure.attempt_id,
                failed_at=failure.failed_at,
                failure_kind=failure.failure_kind,
                recovered=failure.recovered,
            )
            for failure in failures
        )
        latest = history_view[-1]
        summaries.append(
            MistakeSummary(
                problem_id=problem_id,
                failure_count=len(history_view),
                last_failed_at=latest.failed_at,
                last_failed_sequence=failures[-1].sequence,
                last_failure_kind=latest.failure_kind,
                current_evidence_recovered=all(item.recovered for item in history_view),
                failure_history=history_view,
            )
        )
    return tuple(summaries)


def _idempotency_match(event: Mapping[str, Any], event_type: str, problem_id: str | None, attempt_id: str | None, payload: Mapping[str, Any]) -> bool:
    if event["event_type"] != event_type or event["problem_id"] != problem_id or event["attempt_id"] != attempt_id:
        return False
    if event_type == "task_implemented":
        return event["payload"].get("submission_sha256") == payload.get("submission_sha256")
    if event_type in {"review_completed", "retention_d2_passed", "retention_d7_passed", "task_mastered"}:
        return event["payload"] == dict(payload)
    return False


def append_event(
    events_path: Path,
    schema_path: Path,
    *,
    profile_id: str,
    event_type: str,
    problem_id: str | None,
    attempt_id: str | None,
    payload: Mapping[str, Any],
    timestamp: datetime | None = None,
    event_id: str | None = None,
) -> AppendResult:
    """Append one event. Concurrent writers are intentionally unsupported."""

    existing = read_events(events_path, schema_path) if events_path.exists() else []
    for candidate in existing:
        if _idempotency_match(candidate, event_type, problem_id, attempt_id, payload):
            return AppendResult(candidate, False)
    recorded_at = timestamp or datetime.now().astimezone()
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise EventError("event timestamp must include a timezone")
    event = {
        "schema_version": 1, "event_id": event_id or f"evt-{uuid4()}",
        "timestamp": recorded_at.isoformat(timespec="seconds"), "profile_id": profile_id,
        "event_type": event_type, "problem_id": problem_id, "attempt_id": attempt_id, "payload": dict(payload),
    }
    validate_event(event, schema_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        stream.flush()
    return AppendResult(event, True)
