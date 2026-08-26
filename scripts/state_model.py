"""Validated, append-only training-state model.

The JSONL ledger is the historical source of truth.  Human-facing Markdown
files may summarize it, but they must never introduce a state transition that
is absent from the ledger.

This module deliberately uses only the Python standard library so state
validation remains available before optional training dependencies are
installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
import json
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
MAX_LEDGER_LINE_BYTES = 64 * 1024
CURRENT_TASK_STATE_START = "<!-- CURRENT_TASK_STATE"
CURRENT_TASK_STATE_END = "END_CURRENT_TASK_STATE -->"

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_EVENT_KEYS = frozenset(
    {
        "schema_version",
        "event_id",
        "task_id",
        "attempt_id",
        "event_type",
        "recorded_on",
        "recorded_at",
        "status_before",
        "status_after",
        "assistance",
        "variant_id",
        "evidence",
        "reason",
    }
)
_ASSISTANCE_KEYS = frozenset({"level", "demonstration_only"})
_EVIDENCE_KEYS = frozenset(
    {"summary", "artifacts", "test_result", "oral_passed"}
)
_CURRENT_TASK_KEYS = frozenset(
    {
        "schema_version",
        "task_id",
        "status",
        "latest_event_id",
        "attempt_id",
        "assistance_level",
        "demonstration_only",
        "requires_independent_variant",
    }
)


class StateValidationError(ValueError):
    """Raised when state cannot be trusted."""


class TaskStatus(str, Enum):
    NOT_STARTED = "not_started"
    ATTEMPTED = "attempted"
    NEEDS_REVISION = "needs_revision"
    IMPLEMENTED = "implemented"
    REVIEWED = "reviewed"
    RETAINED_48H = "retained_48h"
    RETAINED_7D = "retained_7d"
    MASTERED = "mastered"


class AssistanceLevel(str, Enum):
    H0 = "H0"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H5 = "H5"


class TestResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class EventType(str, Enum):
    TASK_REGISTERED = "task_registered"
    LEGACY_IMPORT = "legacy_import"
    ATTEMPT_STARTED = "attempt_started"
    IMPLEMENTATION_VERIFIED = "implementation_verified"
    IMPLEMENTATION_FAILED = "implementation_failed"
    ATTEMPT_ABANDONED = "attempt_abandoned"
    REVIEW_PASSED = "review_passed"
    REVIEW_FAILED = "review_failed"
    RETENTION_48H_PASSED = "retention_48h_passed"
    RETENTION_7D_PASSED = "retention_7d_passed"
    RETENTION_FAILED = "retention_failed"
    MASTERY_PASSED = "mastery_passed"
    REGRESSION_FOUND = "regression_found"
    NOTE = "note"


_LEGAL_TRANSITIONS: Mapping[
    EventType, frozenset[tuple[TaskStatus | None, TaskStatus]]
] = {
    EventType.TASK_REGISTERED: frozenset({(None, TaskStatus.NOT_STARTED)}),
    EventType.ATTEMPT_STARTED: frozenset(
        {
            (TaskStatus.NOT_STARTED, TaskStatus.ATTEMPTED),
            (TaskStatus.NEEDS_REVISION, TaskStatus.ATTEMPTED),
        }
    ),
    EventType.IMPLEMENTATION_VERIFIED: frozenset(
        {(TaskStatus.ATTEMPTED, TaskStatus.IMPLEMENTED)}
    ),
    EventType.IMPLEMENTATION_FAILED: frozenset(
        {(TaskStatus.ATTEMPTED, TaskStatus.NEEDS_REVISION)}
    ),
    EventType.ATTEMPT_ABANDONED: frozenset(
        {(TaskStatus.ATTEMPTED, TaskStatus.NEEDS_REVISION)}
    ),
    EventType.REVIEW_PASSED: frozenset(
        {(TaskStatus.IMPLEMENTED, TaskStatus.REVIEWED)}
    ),
    EventType.REVIEW_FAILED: frozenset(
        {(TaskStatus.IMPLEMENTED, TaskStatus.NEEDS_REVISION)}
    ),
    EventType.RETENTION_48H_PASSED: frozenset(
        {(TaskStatus.REVIEWED, TaskStatus.RETAINED_48H)}
    ),
    EventType.RETENTION_7D_PASSED: frozenset(
        {(TaskStatus.RETAINED_48H, TaskStatus.RETAINED_7D)}
    ),
    EventType.RETENTION_FAILED: frozenset(
        {
            (TaskStatus.REVIEWED, TaskStatus.NEEDS_REVISION),
            (TaskStatus.RETAINED_48H, TaskStatus.NEEDS_REVISION),
            (TaskStatus.RETAINED_7D, TaskStatus.NEEDS_REVISION),
        }
    ),
    EventType.MASTERY_PASSED: frozenset(
        {(TaskStatus.RETAINED_7D, TaskStatus.MASTERED)}
    ),
    EventType.REGRESSION_FOUND: frozenset(
        {
            (TaskStatus.IMPLEMENTED, TaskStatus.NEEDS_REVISION),
            (TaskStatus.REVIEWED, TaskStatus.NEEDS_REVISION),
            (TaskStatus.RETAINED_48H, TaskStatus.NEEDS_REVISION),
            (TaskStatus.RETAINED_7D, TaskStatus.NEEDS_REVISION),
            (TaskStatus.MASTERED, TaskStatus.NEEDS_REVISION),
        }
    ),
}

_ADVANCEMENT_EVENTS = frozenset(
    {
        EventType.IMPLEMENTATION_VERIFIED,
        EventType.REVIEW_PASSED,
        EventType.RETENTION_48H_PASSED,
        EventType.RETENTION_7D_PASSED,
        EventType.MASTERY_PASSED,
    }
)
_RETENTION_EVENTS = frozenset(
    {
        EventType.RETENTION_48H_PASSED,
        EventType.RETENTION_7D_PASSED,
        EventType.MASTERY_PASSED,
    }
)
_ATTEMPT_EVENTS = frozenset(
    {
        EventType.ATTEMPT_STARTED,
        EventType.IMPLEMENTATION_VERIFIED,
        EventType.IMPLEMENTATION_FAILED,
        EventType.ATTEMPT_ABANDONED,
        EventType.REVIEW_PASSED,
        EventType.REVIEW_FAILED,
        EventType.RETENTION_48H_PASSED,
        EventType.RETENTION_7D_PASSED,
        EventType.RETENTION_FAILED,
        EventType.MASTERY_PASSED,
    }
)
_HIGH_ASSISTANCE = frozenset({AssistanceLevel.H4, AssistanceLevel.H5})
_ASSISTANCE_RANK = {
    AssistanceLevel.H0: 0,
    AssistanceLevel.H1: 1,
    AssistanceLevel.H2: 2,
    AssistanceLevel.H3: 3,
    AssistanceLevel.H4: 4,
    AssistanceLevel.H5: 5,
}
_SAME_ATTEMPT_EVENTS = frozenset(
    {
        EventType.IMPLEMENTATION_VERIFIED,
        EventType.IMPLEMENTATION_FAILED,
        EventType.ATTEMPT_ABANDONED,
        EventType.REVIEW_PASSED,
        EventType.REVIEW_FAILED,
    }
)
_NEW_ASSESSMENT_EVENTS = frozenset(
    {
        EventType.ATTEMPT_STARTED,
        EventType.RETENTION_48H_PASSED,
        EventType.RETENTION_7D_PASSED,
        EventType.RETENTION_FAILED,
        EventType.MASTERY_PASSED,
    }
)


@dataclass(frozen=True)
class Assistance:
    level: AssistanceLevel
    demonstration_only: bool


@dataclass(frozen=True)
class Evidence:
    summary: str
    artifacts: tuple[PurePosixPath, ...]
    test_result: TestResult
    oral_passed: bool | None


@dataclass(frozen=True)
class LedgerEvent:
    schema_version: int
    event_id: str
    task_id: str
    attempt_id: str | None
    event_type: EventType
    recorded_on: date | None
    recorded_at: datetime | None
    status_before: TaskStatus | None
    status_after: TaskStatus
    assistance: Assistance
    variant_id: str | None
    evidence: Evidence
    reason: str


@dataclass(frozen=True)
class TaskSnapshot:
    task_id: str
    status: TaskStatus
    latest_event_id: str
    attempt_id: str | None
    assistance_level: AssistanceLevel
    demonstration_only: bool
    recorded_on: date | None
    recorded_at: datetime | None
    reviewed_at: datetime | None
    used_attempt_ids: frozenset[str]
    used_variant_ids: frozenset[str]
    requires_independent_variant: bool


@dataclass(frozen=True)
class CurrentTaskState:
    schema_version: int
    task_id: str
    status: TaskStatus
    latest_event_id: str
    attempt_id: str | None
    assistance_level: AssistanceLevel
    demonstration_only: bool
    requires_independent_variant: bool


def _expect_exact_keys(
    value: Mapping[str, Any], expected: frozenset[str], context: str
) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing keys: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown keys: {', '.join(unknown)}")
        raise StateValidationError(f"{context} has invalid fields ({'; '.join(details)})")


def _expect_mapping(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise StateValidationError(f"{context} must be a JSON object")
    return value


def _expect_nonempty_string(value: Any, context: str, *, limit: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateValidationError(f"{context} must be a non-empty string")
    if len(value) > limit:
        raise StateValidationError(f"{context} exceeds {limit} characters")
    return value


def _expect_identifier(value: Any, context: str) -> str:
    text = _expect_nonempty_string(value, context, limit=128)
    if not _ID_PATTERN.fullmatch(text):
        raise StateValidationError(f"{context} is not a valid identifier")
    return text


def _parse_enum(enum_type: type[Enum], value: Any, context: str) -> Any:
    if not isinstance(value, str):
        raise StateValidationError(f"{context} must be a string")
    try:
        return enum_type(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_type)
        raise StateValidationError(
            f"{context} must be one of: {allowed}"
        ) from error


def _parse_recorded_on(value: Any, context: str) -> date:
    if not isinstance(value, str):
        raise StateValidationError(f"{context} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise StateValidationError(f"{context} must be an ISO date") from error
    if parsed.isoformat() != value:
        raise StateValidationError(f"{context} must use YYYY-MM-DD")
    return parsed


_RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


def _parse_recorded_at(value: Any, context: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339_PATTERN.fullmatch(value):
        raise StateValidationError(
            f"{context} must be a timezone-aware RFC3339 timestamp"
        )
    if value.endswith("-00:00"):
        raise StateValidationError(
            f"{context} must use a known timezone offset, not -00:00"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise StateValidationError(
            f"{context} must be a timezone-aware RFC3339 timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StateValidationError(
            f"{context} must include a timezone offset"
        )
    return parsed


def _parse_relative_path(value: Any, context: str) -> PurePosixPath:
    text = _expect_nonempty_string(value, context, limit=512)
    if "\\" in text or "\x00" in text:
        raise StateValidationError(f"{context} must use a safe POSIX relative path")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise StateValidationError(f"{context} must be a safe repository-relative path")
    if path.parts and re.fullmatch(r"[A-Za-z]:", path.parts[0]):
        raise StateValidationError(f"{context} must not contain a drive prefix")
    return path


def _parse_assistance(value: Any, context: str) -> Assistance:
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _ASSISTANCE_KEYS, context)
    level = _parse_enum(AssistanceLevel, mapping["level"], f"{context}.level")
    demonstration_only = mapping["demonstration_only"]
    if type(demonstration_only) is not bool:
        raise StateValidationError(
            f"{context}.demonstration_only must be a boolean"
        )
    if level is AssistanceLevel.H5 and not demonstration_only:
        raise StateValidationError("H5 assistance must be demonstration_only")
    return Assistance(level=level, demonstration_only=demonstration_only)


def _parse_evidence(value: Any, context: str) -> Evidence:
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _EVIDENCE_KEYS, context)
    summary = _expect_nonempty_string(mapping["summary"], f"{context}.summary")
    raw_artifacts = mapping["artifacts"]
    if not isinstance(raw_artifacts, list):
        raise StateValidationError(f"{context}.artifacts must be a list")
    artifacts = tuple(
        _parse_relative_path(item, f"{context}.artifacts[{index}]")
        for index, item in enumerate(raw_artifacts)
    )
    if len(set(artifacts)) != len(artifacts):
        raise StateValidationError(f"{context}.artifacts contains duplicates")
    test_result = _parse_enum(
        TestResult, mapping["test_result"], f"{context}.test_result"
    )
    oral_passed = mapping["oral_passed"]
    if oral_passed is not None and type(oral_passed) is not bool:
        raise StateValidationError(f"{context}.oral_passed must be boolean or null")
    return Evidence(
        summary=summary,
        artifacts=artifacts,
        test_result=test_result,
        oral_passed=oral_passed,
    )


def parse_event(value: Mapping[str, Any], *, context: str = "event") -> LedgerEvent:
    """Parse and validate one ledger event, without replaying history."""

    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _EVENT_KEYS, context)
    if type(mapping["schema_version"]) is not int or mapping["schema_version"] != SCHEMA_VERSION:
        raise StateValidationError(
            f"{context}.schema_version must equal {SCHEMA_VERSION}"
        )

    attempt_id_value = mapping["attempt_id"]
    attempt_id = (
        None
        if attempt_id_value is None
        else _expect_identifier(attempt_id_value, f"{context}.attempt_id")
    )
    variant_id_value = mapping["variant_id"]
    variant_id = (
        None
        if variant_id_value is None
        else _expect_identifier(variant_id_value, f"{context}.variant_id")
    )
    status_before_value = mapping["status_before"]
    status_before = (
        None
        if status_before_value is None
        else _parse_enum(
            TaskStatus, status_before_value, f"{context}.status_before"
        )
    )

    event = LedgerEvent(
        schema_version=SCHEMA_VERSION,
        event_id=_expect_identifier(mapping["event_id"], f"{context}.event_id"),
        task_id=_expect_identifier(mapping["task_id"], f"{context}.task_id"),
        attempt_id=attempt_id,
        event_type=_parse_enum(
            EventType, mapping["event_type"], f"{context}.event_type"
        ),
        recorded_on=(
            None
            if mapping["recorded_on"] is None
            else _parse_recorded_on(
                mapping["recorded_on"], f"{context}.recorded_on"
            )
        ),
        recorded_at=(
            None
            if mapping["recorded_at"] is None
            else _parse_recorded_at(
                mapping["recorded_at"], f"{context}.recorded_at"
            )
        ),
        status_before=status_before,
        status_after=_parse_enum(
            TaskStatus, mapping["status_after"], f"{context}.status_after"
        ),
        assistance=_parse_assistance(mapping["assistance"], f"{context}.assistance"),
        variant_id=variant_id,
        evidence=_parse_evidence(mapping["evidence"], f"{context}.evidence"),
        reason=_expect_nonempty_string(mapping["reason"], f"{context}.reason", limit=2048),
    )
    _validate_event_contract(event, context)
    return event


def _validate_event_contract(event: LedgerEvent, context: str) -> None:
    if event.event_type is EventType.LEGACY_IMPORT:
        if event.recorded_on is None or event.recorded_at is not None:
            raise StateValidationError(
                f"{context}: legacy_import requires recorded_on and recorded_at=null"
            )
    elif event.recorded_on is not None or event.recorded_at is None:
        raise StateValidationError(
            f"{context}: non-legacy events require recorded_on=null and a "
            "timezone-aware recorded_at"
        )

    transition = (event.status_before, event.status_after)
    if event.event_type is EventType.LEGACY_IMPORT:
        if event.status_before is not None:
            raise StateValidationError(
                f"{context}: legacy_import must start without a previous status"
            )
        if event.status_after in {
            TaskStatus.RETAINED_48H,
            TaskStatus.RETAINED_7D,
            TaskStatus.MASTERED,
        }:
            raise StateValidationError(
                f"{context}: legacy_import cannot establish retention or mastery"
            )
        if event.status_after in {TaskStatus.IMPLEMENTED, TaskStatus.REVIEWED}:
            if event.evidence.test_result is not TestResult.PASSED:
                raise StateValidationError(
                    f"{context}: imported implemented/reviewed state requires "
                    "passing test evidence"
                )
            if not event.evidence.artifacts:
                raise StateValidationError(
                    f"{context}: imported implemented/reviewed state requires "
                    "at least one evidence artifact"
                )
        if (
            event.status_after is TaskStatus.REVIEWED
            and event.evidence.oral_passed is not True
        ):
            raise StateValidationError(
                f"{context}: imported reviewed state requires oral_passed=true"
            )
    elif event.event_type is EventType.NOTE:
        if event.status_before is None or event.status_before is not event.status_after:
            raise StateValidationError(
                f"{context}: note must preserve an existing status"
            )
    elif transition not in _LEGAL_TRANSITIONS[event.event_type]:
        before = "none" if event.status_before is None else event.status_before.value
        raise StateValidationError(
            f"{context}: {event.event_type.value} cannot transition "
            f"{before} -> {event.status_after.value}"
        )

    if event.event_type in _ATTEMPT_EVENTS and event.attempt_id is None:
        raise StateValidationError(
            f"{context}: {event.event_type.value} requires attempt_id"
        )
    if event.event_type is EventType.TASK_REGISTERED and event.attempt_id is not None:
        raise StateValidationError(f"{context}: task_registered must not have attempt_id")

    if event.event_type in _ADVANCEMENT_EVENTS:
        if event.evidence.test_result is not TestResult.PASSED:
            raise StateValidationError(
                f"{context}: advancement requires passing test evidence"
            )
        if not event.evidence.artifacts:
            raise StateValidationError(
                f"{context}: advancement requires at least one evidence artifact"
            )

    if event.event_type in {EventType.REVIEW_PASSED, EventType.MASTERY_PASSED}:
        if event.evidence.oral_passed is not True:
            raise StateValidationError(
                f"{context}: {event.event_type.value} requires oral_passed=true"
            )

    if event.event_type in _RETENTION_EVENTS:
        if event.assistance.level is not AssistanceLevel.H0:
            raise StateValidationError(
                f"{context}: retention and mastery evidence must use H0"
            )
        if event.assistance.demonstration_only:
            raise StateValidationError(
                f"{context}: demonstration-only work cannot prove retention"
            )
        if event.variant_id is None:
            raise StateValidationError(
                f"{context}: retention and mastery require a fresh variant_id"
            )
    elif event.variant_id is not None:
        raise StateValidationError(
            f"{context}: variant_id is reserved for retention and mastery evidence"
        )


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StateValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_ledger(path: Path) -> list[LedgerEvent]:
    """Load a UTF-8 JSONL ledger and reject ambiguous input."""

    try:
        raw = path.read_bytes()
    except OSError as error:
        raise StateValidationError(f"cannot read ledger {path.name}: {error.strerror}") from error
    if not raw:
        raise StateValidationError("ledger must contain at least one event")
    if not raw.endswith(b"\n"):
        raise StateValidationError("ledger must end with a newline")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise StateValidationError("ledger must be valid UTF-8") from error

    events: list[LedgerEvent] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise StateValidationError(f"ledger line {line_number} must not be blank")
        if len(line.encode("utf-8")) > MAX_LEDGER_LINE_BYTES:
            raise StateValidationError(
                f"ledger line {line_number} exceeds {MAX_LEDGER_LINE_BYTES} bytes"
            )
        try:
            value = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except StateValidationError as error:
            raise StateValidationError(f"ledger line {line_number}: {error}") from error
        except json.JSONDecodeError as error:
            raise StateValidationError(
                f"ledger line {line_number} is not valid JSON: {error.msg}"
            ) from error
        events.append(parse_event(value, context=f"ledger line {line_number}"))
    return events


def replay_events(events: Iterable[LedgerEvent]) -> dict[str, TaskSnapshot]:
    """Replay events and return the latest trusted snapshot for every task."""

    snapshots: dict[str, TaskSnapshot] = {}
    event_ids: set[str] = set()

    for position, event in enumerate(events, start=1):
        if event.event_id in event_ids:
            raise StateValidationError(f"event {position}: duplicate event_id {event.event_id}")
        event_ids.add(event.event_id)
        previous = snapshots.get(event.task_id)

        if previous is None:
            if event.status_before is not None:
                raise StateValidationError(
                    f"event {position}: first event for {event.task_id} must start from null"
                )
            if event.event_type not in {
                EventType.TASK_REGISTERED,
                EventType.LEGACY_IMPORT,
            }:
                raise StateValidationError(
                    f"event {position}: first event must register or legacy-import the task"
                )
            used_variants: set[str] = set()
            used_attempts = {event.attempt_id} if event.attempt_id is not None else set()
            # A date-only legacy import cannot prove the exact review instant
            # needed by later retention gates.  Only a future, timestamped
            # review_passed event establishes this baseline.
            reviewed_at: datetime | None = None
            requires_independent_variant = (
                event.assistance.level in _HIGH_ASSISTANCE
                or event.assistance.demonstration_only
            )
        else:
            if event.event_type is EventType.LEGACY_IMPORT:
                raise StateValidationError(
                    f"event {position}: legacy_import is only valid as a task's first event"
                )
            if event.status_before is not previous.status:
                raise StateValidationError(
                    f"event {position}: status chain for {event.task_id} expected "
                    f"{previous.status.value}, found "
                    f"{event.status_before.value if event.status_before else 'null'}"
                )
            if previous.recorded_at is not None:
                if event.recorded_at is None or event.recorded_at < previous.recorded_at:
                    raise StateValidationError(
                        f"event {position}: recorded_at moves backwards for {event.task_id}"
                    )
            elif previous.recorded_on is not None:
                if event.recorded_at is None or event.recorded_at.date() < previous.recorded_on:
                    raise StateValidationError(
                        f"event {position}: recorded_at predates legacy state for {event.task_id}"
                    )
            used_variants = set(previous.used_variant_ids)
            used_attempts = set(previous.used_attempt_ids)
            reviewed_at = previous.reviewed_at
            requires_independent_variant = previous.requires_independent_variant

            if event.event_type is EventType.NOTE:
                note_changes: list[str] = []
                if event.attempt_id != previous.attempt_id:
                    note_changes.append("attempt_id")
                if event.assistance.level is not previous.assistance_level:
                    note_changes.append("assistance level")
                if (
                    event.assistance.demonstration_only
                    is not previous.demonstration_only
                ):
                    note_changes.append("demonstration_only")
                if note_changes:
                    raise StateValidationError(
                        f"event {position}: note cannot change "
                        + ", ".join(note_changes)
                    )

            if event.event_type in _SAME_ATTEMPT_EVENTS:
                if event.attempt_id != previous.attempt_id:
                    raise StateValidationError(
                        f"event {position}: {event.event_type.value} must preserve "
                        "the active attempt_id"
                    )
                if (
                    _ASSISTANCE_RANK[event.assistance.level]
                    < _ASSISTANCE_RANK[previous.assistance_level]
                ):
                    raise StateValidationError(
                        f"event {position}: assistance cannot be downgraded within an attempt"
                    )
                if previous.demonstration_only and not event.assistance.demonstration_only:
                    raise StateValidationError(
                        f"event {position}: demonstration_only cannot be cleared within an attempt"
                    )

            if event.event_type in _NEW_ASSESSMENT_EVENTS:
                if event.attempt_id in used_attempts:
                    raise StateValidationError(
                        f"event {position}: attempt_id {event.attempt_id} has already been used"
                    )
                if event.attempt_id is not None:
                    used_attempts.add(event.attempt_id)

        if event.variant_id is not None:
            if event.variant_id in used_variants:
                raise StateValidationError(
                    f"event {position}: variant_id {event.variant_id} is not fresh"
                )
            used_variants.add(event.variant_id)

        if event.event_type is EventType.REVIEW_PASSED:
            reviewed_at = event.recorded_at
        elif event.status_after is TaskStatus.NEEDS_REVISION:
            reviewed_at = None

        if event.event_type is EventType.RETENTION_48H_PASSED:
            if reviewed_at is None:
                raise StateValidationError(
                    f"event {position}: retained_48h requires a timestamped "
                    "review_passed baseline"
                )
            if event.recorded_at is None or event.recorded_at < reviewed_at + timedelta(hours=48):
                raise StateValidationError(
                    f"event {position}: retained_48h requires at least 48 elapsed hours"
                )
        elif event.event_type is EventType.RETENTION_7D_PASSED:
            if reviewed_at is None:
                raise StateValidationError(
                    f"event {position}: retained_7d requires a timestamped "
                    "review_passed baseline"
                )
            if event.recorded_at is None or event.recorded_at < reviewed_at + timedelta(days=7):
                raise StateValidationError(
                    f"event {position}: retained_7d requires at least seven elapsed days"
                )
        elif event.event_type is EventType.MASTERY_PASSED:
            if reviewed_at is None:
                raise StateValidationError(
                    f"event {position}: mastered requires a timestamped "
                    "review_passed baseline"
                )
            if event.recorded_at is None or event.recorded_at < reviewed_at + timedelta(days=21):
                raise StateValidationError(
                    f"event {position}: mastered requires at least 21 elapsed days"
                )

        substantive_help_event = event.event_type in {
            EventType.LEGACY_IMPORT,
            EventType.ATTEMPT_STARTED,
            EventType.IMPLEMENTATION_VERIFIED,
            EventType.REVIEW_PASSED,
        }
        if substantive_help_event and (
            event.assistance.level in _HIGH_ASSISTANCE
            or event.assistance.demonstration_only
        ):
            requires_independent_variant = True
        if event.event_type in _RETENTION_EVENTS:
            # Static validation already requires H0 and a unique variant.  This
            # is the independent evidence that clears H4/H5 demonstration debt.
            requires_independent_variant = False

        snapshot_attempt_id = event.attempt_id
        snapshot_assistance_level = event.assistance.level
        snapshot_demonstration_only = event.assistance.demonstration_only
        if event.event_type is EventType.NOTE and previous is not None:
            # Notes append context only.  They must never become a new source
            # of truth for attempt/help metadata or erase outstanding debt.
            snapshot_attempt_id = previous.attempt_id
            snapshot_assistance_level = previous.assistance_level
            snapshot_demonstration_only = previous.demonstration_only

        snapshots[event.task_id] = TaskSnapshot(
            task_id=event.task_id,
            status=event.status_after,
            latest_event_id=event.event_id,
            attempt_id=snapshot_attempt_id,
            assistance_level=snapshot_assistance_level,
            demonstration_only=snapshot_demonstration_only,
            recorded_on=event.recorded_on,
            recorded_at=event.recorded_at,
            reviewed_at=reviewed_at,
            used_attempt_ids=frozenset(used_attempts),
            used_variant_ids=frozenset(used_variants),
            requires_independent_variant=requires_independent_variant,
        )

    return snapshots


def parse_current_task_state(markdown: str) -> CurrentTaskState:
    """Parse the single hidden JSON state block from CURRENT_TASK.md."""

    start_count = markdown.count(CURRENT_TASK_STATE_START)
    end_count = markdown.count(CURRENT_TASK_STATE_END)
    if start_count != 1 or end_count != 1:
        raise StateValidationError(
            "CURRENT_TASK.md must contain exactly one machine-readable state block"
        )
    start = markdown.index(CURRENT_TASK_STATE_START) + len(CURRENT_TASK_STATE_START)
    end = markdown.index(CURRENT_TASK_STATE_END, start)
    payload = markdown[start:end].strip()
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except StateValidationError as error:
        raise StateValidationError(f"CURRENT_TASK state block: {error}") from error
    except json.JSONDecodeError as error:
        raise StateValidationError(
            f"CURRENT_TASK state block is not valid JSON: {error.msg}"
        ) from error
    mapping = _expect_mapping(value, "CURRENT_TASK state block")
    _expect_exact_keys(mapping, _CURRENT_TASK_KEYS, "CURRENT_TASK state block")
    if type(mapping["schema_version"]) is not int or mapping["schema_version"] != SCHEMA_VERSION:
        raise StateValidationError(
            f"CURRENT_TASK state block schema_version must equal {SCHEMA_VERSION}"
        )
    attempt_value = mapping["attempt_id"]
    attempt_id = (
        None
        if attempt_value is None
        else _expect_identifier(attempt_value, "CURRENT_TASK attempt_id")
    )
    demonstration_only = mapping["demonstration_only"]
    if type(demonstration_only) is not bool:
        raise StateValidationError("CURRENT_TASK demonstration_only must be boolean")
    requires_independent_variant = mapping["requires_independent_variant"]
    if type(requires_independent_variant) is not bool:
        raise StateValidationError(
            "CURRENT_TASK requires_independent_variant must be boolean"
        )
    return CurrentTaskState(
        schema_version=SCHEMA_VERSION,
        task_id=_expect_identifier(mapping["task_id"], "CURRENT_TASK task_id"),
        status=_parse_enum(TaskStatus, mapping["status"], "CURRENT_TASK status"),
        latest_event_id=_expect_identifier(
            mapping["latest_event_id"], "CURRENT_TASK latest_event_id"
        ),
        attempt_id=attempt_id,
        assistance_level=_parse_enum(
            AssistanceLevel,
            mapping["assistance_level"],
            "CURRENT_TASK assistance_level",
        ),
        demonstration_only=demonstration_only,
        requires_independent_variant=requires_independent_variant,
    )


def validate_current_task(
    current: CurrentTaskState, snapshots: Mapping[str, TaskSnapshot]
) -> TaskSnapshot:
    """Ensure the Markdown snapshot exactly matches the ledger replay."""

    snapshot = snapshots.get(current.task_id)
    if snapshot is None:
        raise StateValidationError(
            f"CURRENT_TASK references unknown task {current.task_id}"
        )
    comparisons = {
        "status": (current.status, snapshot.status),
        "latest_event_id": (current.latest_event_id, snapshot.latest_event_id),
        "attempt_id": (current.attempt_id, snapshot.attempt_id),
        "assistance_level": (
            current.assistance_level,
            snapshot.assistance_level,
        ),
        "demonstration_only": (
            current.demonstration_only,
            snapshot.demonstration_only,
        ),
        "requires_independent_variant": (
            current.requires_independent_variant,
            snapshot.requires_independent_variant,
        ),
    }
    mismatches = [name for name, (actual, expected) in comparisons.items() if actual != expected]
    if mismatches:
        raise StateValidationError(
            "CURRENT_TASK state block disagrees with ledger: " + ", ".join(mismatches)
        )
    return snapshot


def validate_artifacts(
    events: Iterable[LedgerEvent], *, repo_root: Path
) -> None:
    """Require evidence artifacts to be regular, in-repository files."""

    try:
        root = repo_root.resolve(strict=True)
    except OSError as error:
        raise StateValidationError("repository root is not accessible") from error
    if not root.is_dir():
        raise StateValidationError("repository root must be a directory")
    for event in events:
        for relative in event.evidence.artifacts:
            candidate = repo_root.joinpath(*relative.parts)
            component = repo_root
            for part in relative.parts:
                component = component / part
                try:
                    component_stat = component.lstat()
                except OSError as error:
                    raise StateValidationError(
                        f"event {event.event_id}: evidence artifact does not exist: {relative}"
                    ) from error
                attributes = getattr(component_stat, "st_file_attributes", 0)
                reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                if stat.S_ISLNK(component_stat.st_mode) or (
                    reparse_flag and attributes & reparse_flag
                ):
                    raise StateValidationError(
                        f"event {event.event_id}: evidence path must not use links: {relative}"
                    )
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as error:
                raise StateValidationError(
                    f"event {event.event_id}: evidence artifact does not exist: {relative}"
                ) from error
            try:
                resolved.relative_to(root)
            except ValueError as error:
                raise StateValidationError(
                    f"event {event.event_id}: evidence artifact escapes repository: {relative}"
                ) from error
            if candidate.is_symlink() or not resolved.is_file():
                raise StateValidationError(
                    f"event {event.event_id}: evidence artifact must be a regular file: {relative}"
                )


def validate_append_only(*, base: bytes, current: bytes) -> None:
    """Reject edits or deletion of ledger bytes already present in a base copy."""

    if base and not base.endswith(b"\n"):
        raise StateValidationError("base ledger must end with a newline")
    if not current.startswith(base):
        raise StateValidationError(
            "ledger is not append-only: existing base bytes were changed or removed"
        )
