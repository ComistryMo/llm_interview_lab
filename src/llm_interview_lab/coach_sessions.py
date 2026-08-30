"""Profile-local, answer-safe persistence for desktop Coach conversations.

The Coach transcript is deliberately separate from Practice events and
Interview sessions.  It is a resumable UI workspace, not evidence for
mastery, scoring, or progress.  This module keeps the format small and
validates every read/write so a damaged local file cannot make the controller
walk outside the selected Profile.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping
from uuid import uuid4

from .workspace import (
    ensure_profile_is_ignored,
    ensure_profile_path_is_safe,
    load_profile,
    profile_paths,
    validate_profile_id,
)


SCHEMA_VERSION = 1
SESSION_ID_RE = re.compile(r"^coach-[a-f0-9]{12,64}$")
MESSAGE_ID_RE = re.compile(r"^msg-[a-f0-9]{12,64}$")
MODES = frozenset({"coach", "teacher", "reviewer"})
MESSAGE_ROLES = frozenset({"user", "assistant", "system", "tool", "approval", "error"})
STATUSES = frozenset({"idle", "streaming", "stopped", "error"})
MAX_SESSIONS = 50
MAX_MESSAGES = 400
MAX_TEXT = 200_000


class CoachSessionError(RuntimeError):
    """Raised when local Coach session data cannot be safely used."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _session_path(repo_root: Path, profile_id: str) -> Path:
    """Resolve only the selected Profile's transcript path."""

    validate_profile_id(profile_id)
    paths = profile_paths(repo_root, profile_id)
    # Loading the profile first prevents a missing/foreign path from being
    # treated as a valid session store.  No sibling Profile is enumerated.
    load_profile(paths, repo_root)
    return ensure_profile_path_is_safe(
        repo_root,
        profile_id,
        paths.root / "coach" / "sessions.json",
    )


def coach_sessions_path(repo_root: Path, profile_id: str) -> Path:
    """Public path helper used by tests and the desktop controller."""

    return _session_path(repo_root, profile_id)


def _empty_store(profile_id: str) -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "profile_id": profile_id, "sessions": []}


def _error(location: str, message: str) -> CoachSessionError:
    return CoachSessionError(f"invalid Coach session data at {location}: {message}")


def _validate_message(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(location, "message must be an object")
    required = {"message_id", "role", "content", "created_at"}
    if not required.issubset(value):
        raise _error(location, "message is missing required fields")
    message_id = value["message_id"]
    if not isinstance(message_id, str) or MESSAGE_ID_RE.fullmatch(message_id) is None:
        raise _error(f"{location}.message_id", "invalid message id")
    role = value["role"]
    if role not in MESSAGE_ROLES:
        raise _error(f"{location}.role", "unsupported message role")
    content = value["content"]
    if not isinstance(content, str) or len(content) > MAX_TEXT:
        raise _error(f"{location}.content", "message content is invalid or too large")
    created_at = value["created_at"]
    if not isinstance(created_at, str) or not created_at.strip():
        raise _error(f"{location}.created_at", "timestamp is required")
    # Keep optional metadata deliberately JSON-like and bounded.  Metadata is
    # for provider/model labels and never carries credentials.
    metadata = value.get("metadata", {})
    if not isinstance(metadata, dict):
        raise _error(f"{location}.metadata", "metadata must be an object")
    return {
        "message_id": message_id,
        "role": role,
        "content": content,
        "created_at": created_at,
        "metadata": dict(metadata),
    }


def _validate_context(value: Any, location: str) -> dict[str, Any]:
    if value is None:
        return {"references": [], "hashes": {}}
    if not isinstance(value, dict):
        raise _error(location, "context must be an object")
    references = value.get("references", [])
    hashes = value.get("hashes", {})
    if not isinstance(references, list) or not all(isinstance(item, str) for item in references):
        raise _error(f"{location}.references", "references must be strings")
    if not isinstance(hashes, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in hashes.items()
    ):
        raise _error(f"{location}.hashes", "hashes must be a string map")
    if len(references) > 100 or len(hashes) > 100:
        raise _error(location, "context reference list is too large")
    return {"references": list(dict.fromkeys(references)), "hashes": dict(hashes)}


def _validate_session(value: Any, location: str, profile_id: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error(location, "session must be an object")
    required = {
        "session_id",
        "profile_id",
        "title",
        "mode",
        "provider_kind",
        "problem_id",
        "status",
        "created_at",
        "updated_at",
        "draft",
        "context",
        "messages",
    }
    if not required.issubset(value):
        missing = sorted(required.difference(value))
        raise _error(location, "missing fields: " + ", ".join(missing))
    session_id = value["session_id"]
    if not isinstance(session_id, str) or SESSION_ID_RE.fullmatch(session_id) is None:
        raise _error(f"{location}.session_id", "invalid session id")
    if value["profile_id"] != profile_id:
        raise _error(f"{location}.profile_id", "profile id does not match the selected Profile")
    if not isinstance(value["title"], str) or not value["title"].strip() or len(value["title"]) > 200:
        raise _error(f"{location}.title", "title must be non-empty and bounded")
    if value["mode"] not in MODES:
        raise _error(f"{location}.mode", "unsupported Coach mode")
    if not isinstance(value["provider_kind"], str) or len(value["provider_kind"]) > 100:
        raise _error(f"{location}.provider_kind", "provider kind is invalid")
    problem_id = value["problem_id"]
    if problem_id is not None and (not isinstance(problem_id, str) or len(problem_id) > 200):
        raise _error(f"{location}.problem_id", "problem id is invalid")
    if value["status"] not in STATUSES:
        raise _error(f"{location}.status", "unsupported session status")
    for field in ("created_at", "updated_at"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise _error(f"{location}.{field}", "timestamp is required")
    if not isinstance(value["draft"], str) or len(value["draft"]) > MAX_TEXT:
        raise _error(f"{location}.draft", "draft is invalid or too large")
    context = _validate_context(value["context"], f"{location}.context")
    messages = value["messages"]
    if not isinstance(messages, list) or len(messages) > MAX_MESSAGES:
        raise _error(f"{location}.messages", "messages must be a bounded list")
    checked_messages = [_validate_message(item, f"{location}.messages[{index}]") for index, item in enumerate(messages)]
    message_ids = [item["message_id"] for item in checked_messages]
    if len(message_ids) != len(set(message_ids)):
        raise _error(f"{location}.messages", "message ids must be unique")
    last_turn = value.get("last_turn")
    if last_turn is not None and not isinstance(last_turn, dict):
        raise _error(f"{location}.last_turn", "last turn must be an object")
    if isinstance(last_turn, dict):
        # Newer writers persist the complete async identity.  Older stores may
        # omit these optional keys, but a present identity must never point at
        # another Profile/session or smuggle arbitrary values into retries.
        if last_turn.get("profile_id") not in {None, profile_id}:
            raise _error(f"{location}.last_turn.profile_id", "profile id does not match session")
        if last_turn.get("session_id") not in {None, session_id}:
            raise _error(f"{location}.last_turn.session_id", "session id does not match session")
        for field in ("operation_id", "message_id", "provider_kind", "provider_id", "model", "mode"):
            if field in last_turn and not isinstance(last_turn[field], str):
                raise _error(f"{location}.last_turn.{field}", "must be a string")
        for field in ("include_submission", "include_test_output"):
            if field in last_turn and type(last_turn[field]) is not bool:
                raise _error(f"{location}.last_turn.{field}", "must be a boolean")
    # Preserve optional provider/model fields while preventing non-JSON values
    # from leaking into the store.
    provider_id = value.get("provider_id", "")
    model = value.get("model", "")
    if not isinstance(provider_id, str) or not isinstance(model, str):
        raise _error(location, "provider metadata is invalid")
    return {
        "session_id": session_id,
        "profile_id": profile_id,
        "title": value["title"].strip(),
        "mode": value["mode"],
        "provider_kind": value["provider_kind"],
        "provider_id": provider_id,
        "model": model,
        "problem_id": problem_id,
        "status": value["status"],
        "created_at": value["created_at"],
        "updated_at": value["updated_at"],
        "draft": value["draft"],
        "context": context,
        "messages": checked_messages,
        "last_turn": dict(last_turn) if isinstance(last_turn, dict) else None,
    }


def validate_coach_store(value: Any, profile_id: str) -> dict[str, Any]:
    """Validate and normalize one profile's complete session store."""

    if not isinstance(value, dict):
        raise _error("<root>", "store must be an object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise _error("schema_version", "unsupported schema version")
    if value.get("profile_id") != profile_id:
        raise _error("profile_id", "store belongs to another Profile")
    sessions = value.get("sessions")
    if not isinstance(sessions, list) or len(sessions) > MAX_SESSIONS:
        raise _error("sessions", "sessions must be a bounded list")
    checked = [_validate_session(item, f"sessions[{index}]", profile_id) for index, item in enumerate(sessions)]
    ids = [item["session_id"] for item in checked]
    if len(ids) != len(set(ids)):
        raise _error("sessions", "session ids must be unique")
    return {"schema_version": SCHEMA_VERSION, "profile_id": profile_id, "sessions": checked}


def load_coach_sessions(repo_root: Path, profile_id: str) -> list[dict[str, Any]]:
    """Load only the selected Profile's sessions; missing means empty."""

    path = _session_path(repo_root, profile_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CoachSessionError("Coach sessions could not be read") from error
    return validate_coach_store(raw, profile_id)["sessions"]


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    encoded = (json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise CoachSessionError("Coach sessions could not be written") from error


def write_coach_sessions(
    repo_root: Path, profile_id: str, sessions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Atomically persist a validated list under the selected Profile."""

    path = _session_path(repo_root, profile_id)
    ensure_profile_is_ignored(repo_root, profile_id)
    parent = path.parent
    ensure_profile_path_is_safe(repo_root, profile_id, parent)
    if parent.exists() and (not parent.is_dir() or parent.is_symlink()):
        raise CoachSessionError("Profile Coach directory is invalid")
    parent.mkdir(parents=True, exist_ok=True)
    checked = validate_coach_store(
        {"schema_version": SCHEMA_VERSION, "profile_id": profile_id, "sessions": sessions},
        profile_id,
    )
    _atomic_write(path, checked)
    return checked["sessions"]


def new_coach_session(
    repo_root: Path,
    profile_id: str,
    *,
    mode: str = "coach",
    provider_kind: str = "none",
    problem_id: str | None = None,
    title: str | None = None,
    provider_id: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Create and persist one empty resumable conversation."""

    if mode not in MODES:
        raise CoachSessionError("mode must be coach, teacher, or reviewer")
    sessions = load_coach_sessions(repo_root, profile_id)
    if len(sessions) >= MAX_SESSIONS:
        raise CoachSessionError("too many Coach sessions; delete an old session first")
    timestamp = _now()
    session = {
        "session_id": f"coach-{uuid4().hex}",
        "profile_id": profile_id,
        "title": (title or "新建教练会话").strip()[:200] or "新建教练会话",
        "mode": mode,
        "provider_kind": provider_kind or "none",
        "provider_id": provider_id or "",
        "model": model or "",
        "problem_id": problem_id,
        "status": "idle",
        "created_at": timestamp,
        "updated_at": timestamp,
        "draft": "",
        "context": {"references": [], "hashes": {}},
        "messages": [],
        "last_turn": None,
    }
    sessions.insert(0, session)
    write_coach_sessions(repo_root, profile_id, sessions)
    return session


def delete_coach_session(repo_root: Path, profile_id: str, session_id: str) -> bool:
    sessions = load_coach_sessions(repo_root, profile_id)
    remaining = [item for item in sessions if item["session_id"] != session_id]
    if len(remaining) == len(sessions):
        return False
    write_coach_sessions(repo_root, profile_id, remaining)
    return True


def _ensure_session_id(session: Mapping[str, Any], profile_id: str) -> None:
    if session.get("profile_id") != profile_id:
        raise CoachSessionError("session belongs to another Profile")
    if not isinstance(session.get("session_id"), str):
        raise CoachSessionError("session id is missing")


def update_coach_session(
    repo_root: Path,
    profile_id: str,
    session: dict[str, Any],
) -> dict[str, Any]:
    """Replace one session after validating its identity and fields."""

    _ensure_session_id(session, profile_id)
    sessions = load_coach_sessions(repo_root, profile_id)
    found = False
    updated: list[dict[str, Any]] = []
    for item in sessions:
        if item["session_id"] == session["session_id"]:
            found = True
            updated.append(session)
        else:
            updated.append(item)
    if not found:
        raise CoachSessionError("Coach session no longer exists")
    checked = write_coach_sessions(repo_root, profile_id, updated)
    return next(item for item in checked if item["session_id"] == session["session_id"])


def message(
    role: str,
    content: str,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a validated message object for Controller use."""

    if role not in MESSAGE_ROLES:
        raise CoachSessionError("unsupported Coach message role")
    item = {
        "message_id": f"msg-{uuid4().hex}",
        "role": role,
        "content": str(content),
        "created_at": _now(),
        "metadata": dict(metadata or {}),
    }
    return _validate_message(item, "message")


__all__ = [
    "CoachSessionError",
    "MESSAGE_ROLES",
    "MODES",
    "STATUSES",
    "coach_sessions_path",
    "delete_coach_session",
    "load_coach_sessions",
    "message",
    "new_coach_session",
    "update_coach_session",
    "validate_coach_store",
    "write_coach_sessions",
]
