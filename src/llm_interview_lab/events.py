"""Append-only workspace events and their deterministic reducer."""

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


class EventError(RuntimeError):
    """Raised when workspace history is malformed or cannot be appended."""


@dataclass
class AttemptState:
    """Reduced state for one problem attempt."""

    problem_id: str
    attempt_id: str
    submission_relpath: str | None = None
    implemented: bool = False
    revision_required: bool = False
    last_public_test: dict[str, Any] | None = None


@dataclass
class WorkspaceState:
    """State derived strictly from physical JSONL order."""

    profile_id: str | None = None
    current_problem_id: str | None = None
    current_attempt_id: str | None = None
    assistance_level: str | None = None
    attempts: dict[tuple[str, str], AttemptState] = field(default_factory=dict)

    def attempt(self, problem_id: str, attempt_id: str) -> AttemptState | None:
        return self.attempts.get((problem_id, attempt_id))

    def current_attempt(self) -> AttemptState | None:
        if self.current_problem_id is None or self.current_attempt_id is None:
            return None
        return self.attempt(self.current_problem_id, self.current_attempt_id)

    def problem_implemented(self, problem_id: str) -> bool:
        return any(
            attempt.implemented
            for (candidate, _), attempt in self.attempts.items()
            if candidate == problem_id
        )


@dataclass(frozen=True)
class AppendResult:
    """Result of an append, including idempotent no-op information."""

    event: dict[str, Any]
    appended: bool


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(
            schema_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EventError("workspace event schema cannot be read") from error
    if not isinstance(data, dict):
        raise EventError("workspace event schema must be a JSON object")
    return data


def _contains_absolute_path(value: Any) -> bool:
    if isinstance(value, str):
        return (
            value.startswith(("/", "\\\\"))
            or WINDOWS_ABSOLUTE_RE.match(value) is not None
        )
    if isinstance(value, Mapping):
        return any(_contains_absolute_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_absolute_path(item) for item in value)
    return False


def _require_nonnegative_int(payload: Mapping[str, Any], name: str) -> None:
    value = payload.get(name)
    if type(value) is not int or value < 0:
        raise EventError(f"{name} must be a non-negative integer")


def _validate_event_contract(event: Mapping[str, Any]) -> None:
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

    if event_type == "public_tests_run":
        required = {
            "submission_sha256",
            "exit_code",
            "status",
            "passed",
            "failed",
            "duration_ms",
        }
        missing = sorted(required.difference(payload))
        if missing:
            raise EventError(f"public_tests_run payload missing: {', '.join(missing)}")
        if not SHA256_RE.fullmatch(str(payload["submission_sha256"])):
            raise EventError("submission_sha256 must be lowercase SHA-256")
        for name in ("exit_code", "passed", "failed", "duration_ms"):
            _require_nonnegative_int(payload, name)
        if payload["status"] not in {"passed", "failed", "error", "timeout"}:
            raise EventError("public test status is invalid")

    if event_type in {"submission_created", "task_implemented"}:
        digest = payload.get("submission_sha256")
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            raise EventError(f"{event_type} requires submission_sha256")


def validate_event(event: Mapping[str, Any], schema_path: Path) -> None:
    """Validate one event against the public schema and event contracts."""

    validator = Draft202012Validator(
        _load_schema(schema_path),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(event), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise EventError(f"invalid event at {location}: {errors[0].message}")
    _validate_event_contract(event)


def read_events(events_path: Path, schema_path: Path) -> list[dict[str, Any]]:
    """Read and validate events without reordering their physical lines."""

    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise EventError("events.jsonl cannot be read") from error
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise EventError(f"events.jsonl contains blank line {line_number}")
        try:
            event = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as error:
            raise EventError(f"invalid JSON on events line {line_number}") from error
        if not isinstance(event, dict):
            raise EventError(f"event line {line_number} must be an object")
        validate_event(event, schema_path)
        events.append(event)
    return events


def reduce_events(events: Iterable[Mapping[str, Any]]) -> WorkspaceState:
    """Reduce events in the supplied order; timestamps never reorder history."""

    state = WorkspaceState()
    for event in events:
        profile_id = str(event["profile_id"])
        if state.profile_id is not None and state.profile_id != profile_id:
            raise EventError("events.jsonl mixes multiple profile IDs")
        state.profile_id = profile_id
        event_type = event["event_type"]
        if event_type == "profile_created":
            continue

        problem_id = str(event["problem_id"])
        attempt_id = str(event["attempt_id"])
        key = (problem_id, attempt_id)
        payload = dict(event["payload"])

        if event_type in {"task_started", "legacy_import"}:
            if key in state.attempts:
                raise EventError(f"attempt started more than once: {problem_id}/{attempt_id}")
            attempt = AttemptState(
                problem_id=problem_id,
                attempt_id=attempt_id,
                submission_relpath=payload.get("submission_relpath"),
                revision_required=bool(payload.get("revision_required", False)),
            )
            state.attempts[key] = attempt
            state.current_problem_id = problem_id
            state.current_attempt_id = attempt_id
            assistance = payload.get("assistance_level")
            if isinstance(assistance, str):
                state.assistance_level = assistance
            continue

        attempt = state.attempts.get(key)
        if attempt is None:
            raise EventError(f"event references unknown attempt: {problem_id}/{attempt_id}")
        if event_type == "public_tests_run":
            attempt.last_public_test = payload
        elif event_type == "task_implemented":
            attempt.implemented = True
            attempt.revision_required = False

    return state


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
    """Append one event; this first version intentionally has no writer lock."""

    existing = read_events(events_path, schema_path) if events_path.exists() else []
    if event_type == "task_implemented":
        digest = payload.get("submission_sha256")
        for candidate in existing:
            if (
                candidate["event_type"] == event_type
                and candidate["problem_id"] == problem_id
                and candidate["attempt_id"] == attempt_id
                and candidate["payload"].get("submission_sha256") == digest
            ):
                return AppendResult(event=candidate, appended=False)

    recorded_at = timestamp or datetime.now().astimezone()
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise EventError("event timestamp must include a timezone")
    event = {
        "schema_version": 1,
        "event_id": event_id or f"evt-{uuid4()}",
        "timestamp": recorded_at.isoformat(timespec="seconds"),
        "profile_id": profile_id,
        "event_type": event_type,
        "problem_id": problem_id,
        "attempt_id": attempt_id,
        "payload": dict(payload),
    }
    validate_event(event, schema_path)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n")
        stream.flush()
    return AppendResult(event=event, appended=True)
