"""Repository-local profiles, initialization, and answer-free attempts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Any, TYPE_CHECKING

from jsonschema import Draft202012Validator
import yaml

from .events import append_event, read_events, reduce_events, WorkspaceState

if TYPE_CHECKING:
    from .catalog import Problem

PROFILE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
PROFILE_SUBDIRECTORIES = ("submissions", "generated", "private_tests", "reviews", "cache", "exports")


class WorkspaceError(RuntimeError):
    """Raised for an invalid repository-local workspace operation."""


@dataclass(frozen=True)
class ProfilePaths:
    root: Path
    profile_file: Path
    events_file: Path
    submissions_root: Path


@dataclass(frozen=True)
class InitResult:
    paths: ProfilePaths
    created: bool


@dataclass(frozen=True)
class StartResult:
    attempt_id: str
    submission_path: Path
    created: bool
    retention_stage: str | None = None


def find_repository_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "curriculum").is_dir() and (directory / "workspace").is_dir():
            return directory
    raise WorkspaceError("run llm-lab inside a cloned llm_interview_lab repository")


def validate_profile_id(profile_id: str) -> str:
    if PROFILE_ID_RE.fullmatch(profile_id) is None:
        raise WorkspaceError("profile ID must start with a lowercase letter and contain only lowercase letters, digits, or hyphens")
    return profile_id


def profile_paths(repo_root: Path, profile_id: str) -> ProfilePaths:
    root = repo_root / "workspace/profiles" / validate_profile_id(profile_id)
    return ProfilePaths(root, root / "profile.yaml", root / "events.jsonl", root / "submissions")


def event_schema_path(repo_root: Path) -> Path:
    return repo_root / "workspace/schema/event.schema.json"


def profile_schema_path(repo_root: Path) -> Path:
    return repo_root / "workspace/schema/profile.schema.json"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorkspaceError(f"{label} cannot be read") from error
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be an object")
    return value


def validate_profile_data(data: Any, repo_root: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise WorkspaceError("profile.yaml must contain an object")
    errors = sorted(Draft202012Validator(_load_json(profile_schema_path(repo_root), "profile schema")).iter_errors(data), key=lambda item: list(item.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise WorkspaceError(f"invalid profile at {location}: {errors[0].message}")
    return data


def load_profile(paths: ProfilePaths, repo_root: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(paths.profile_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise WorkspaceError("profile.yaml cannot be read") from error
    validated = validate_profile_data(data, repo_root)
    if validated["profile_id"] != paths.root.name:
        raise WorkspaceError("profile ID does not match its directory")
    return validated


def _git_path_is_ignored(repo_root: Path, candidate: Path) -> bool:
    relative = candidate.relative_to(repo_root).as_posix()
    result = subprocess.run(["git", "-C", str(repo_root), "check-ignore", "-q", "--", relative], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode not in {0, 1}:
        raise WorkspaceError("Git ignore check could not be completed")
    return result.returncode == 0


def ensure_profile_is_ignored(repo_root: Path, profile_id: str) -> None:
    if not _git_path_is_ignored(repo_root, profile_paths(repo_root, profile_id).events_file):
        raise WorkspaceError("workspace profile path is not ignored by Git")


def init_profile(repo_root: Path, profile_id: str, track_ids: tuple[str, ...] | None = None) -> InitResult:
    paths = profile_paths(repo_root, profile_id)
    ensure_profile_is_ignored(repo_root, profile_id)
    if paths.root.exists():
        if not paths.root.is_dir():
            raise WorkspaceError("profile path exists and is not a directory")
        load_profile(paths, repo_root)
        read_events(paths.events_file, event_schema_path(repo_root))
        return InitResult(paths, False)
    try:
        template = yaml.safe_load((repo_root / "workspace/templates/default/profile.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise WorkspaceError("default profile template cannot be read") from error
    if not isinstance(template, dict):
        raise WorkspaceError("default profile template must be an object")
    template["profile_id"] = profile_id
    template["synthetic"] = False
    if track_ids:
        template["target_roles"] = list(dict.fromkeys(track_ids))
    validate_profile_data(template, repo_root)
    paths.root.mkdir(parents=True, exist_ok=False)
    for name in PROFILE_SUBDIRECTORIES:
        (paths.root / name).mkdir()
    paths.profile_file.write_text(yaml.safe_dump(template, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")
    append_event(paths.events_file, event_schema_path(repo_root), profile_id=profile_id, event_type="profile_created", problem_id=None, attempt_id=None, payload={"synthetic": False, "target_roles": template["target_roles"]})
    return InitResult(paths, True)


def load_workspace_state(repo_root: Path, profile_id: str) -> WorkspaceState:
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    return reduce_events(read_events(paths.events_file, event_schema_path(repo_root)))


def _is_obvious_link(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _create_attempt(repo_root: Path, profile_id: str, problem: "Problem", attempt_id: str, retention_stage: str | None) -> StartResult:
    paths = profile_paths(repo_root, profile_id)
    attempt_dir = paths.submissions_root / problem.id / attempt_id
    submission_path = attempt_dir / "submission.py"
    if attempt_dir.exists():
        raise WorkspaceError("submission path already exists without a matching event")
    if not problem.ready or problem.problem_dir is None:
        raise WorkspaceError("planned problem cannot be started")
    starter = problem.problem_dir / "starter.py"
    if not starter.is_file() or _is_obvious_link(starter):
        raise WorkspaceError("problem starter is missing or unsafe")
    starter_bytes = starter.read_bytes()
    attempt_dir.mkdir(parents=True, exist_ok=False)
    submission_path.write_bytes(starter_bytes)
    payload: dict[str, Any] = {
        "submission_relpath": submission_path.relative_to(repo_root).as_posix(),
        "starter_sha256": hashlib.sha256(starter_bytes).hexdigest(),
    }
    if retention_stage:
        payload.update({"retention_stage": retention_stage, "variant_contract": problem.raw["retention"][retention_stage]})
    append_event(paths.events_file, event_schema_path(repo_root), profile_id=profile_id, event_type="task_started", problem_id=problem.id, attempt_id=attempt_id, payload=payload)
    return StartResult(attempt_id, submission_path, True, retention_stage)


def start_problem(repo_root: Path, profile_id: str, problem: "Problem") -> StartResult:
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    state = reduce_events(read_events(paths.events_file, event_schema_path(repo_root)))
    initial = [attempt for attempt in state.attempts_for(problem.id) if attempt.retention_stage is None]
    if state.problem_implemented(problem.id):
        raise WorkspaceError("problem is already implemented; use retain after review")
    if initial:
        attempt = initial[-1]
        if attempt.submission_relpath is None:
            raise WorkspaceError("existing attempt has no submission path")
        existing = repo_root.joinpath(*attempt.submission_relpath.split("/"))
        if not existing.is_file():
            raise WorkspaceError("existing attempt submission is missing")
        return StartResult(attempt.attempt_id, existing, False)
    return _create_attempt(repo_root, profile_id, problem, "attempt-0001", None)


def retention_due_at(state: WorkspaceState, problem_id: str, stage: str) -> datetime:
    if stage not in {"d2", "d7"}:
        raise WorkspaceError("retention stage must be d2 or d7")
    reviewed_at = state.reviewed_at.get(problem_id)
    if reviewed_at is None:
        raise WorkspaceError("initial review must pass before retention")
    return reviewed_at + timedelta(days=2 if stage == "d2" else 7)


def start_retention(repo_root: Path, profile_id: str, problem: "Problem", stage: str, now: datetime | None = None) -> StartResult:
    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    state = reduce_events(read_events(paths.events_file, event_schema_path(repo_root)))
    if stage == "d2" and problem.id in state.retained_d2 or stage == "d7" and problem.id in state.retained_d7:
        raise WorkspaceError(f"{stage} retention already passed")
    if stage == "d7" and problem.id not in state.retained_d2:
        raise WorkspaceError("D+2 retention must pass before D+7")
    current_time = now or datetime.now().astimezone()
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise WorkspaceError("retention clock must include a timezone")
    due = retention_due_at(state, problem.id, stage)
    if current_time < due:
        raise WorkspaceError(f"{stage} retention is not due until {due.isoformat(timespec='seconds')}")
    existing = [attempt for attempt in state.attempts_for(problem.id) if attempt.retention_stage == stage]
    if existing:
        attempt = existing[-1]
        assert attempt.submission_relpath is not None
        path = repo_root.joinpath(*attempt.submission_relpath.split("/"))
        if not path.is_file():
            raise WorkspaceError("retention submission is missing")
        return StartResult(attempt.attempt_id, path, False, stage)
    attempt_id = f"attempt-{len(state.attempts_for(problem.id)) + 1:04d}"
    return _create_attempt(repo_root, profile_id, problem, attempt_id, stage)
