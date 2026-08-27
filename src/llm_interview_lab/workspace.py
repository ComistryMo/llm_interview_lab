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
PROFILE_SUBDIRECTORIES = (
    "submissions",
    "generated",
    "private_tests",
    "reviews",
    "cache",
    "exports",
    "materials",
    "interviews",
)


class WorkspaceError(RuntimeError):
    """Raised for an invalid repository-local workspace operation."""


@dataclass(frozen=True)
class ProfilePaths:
    root: Path
    profile_file: Path
    events_file: Path
    submissions_root: Path
    materials_root: Path
    interviews_root: Path


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
    return ProfilePaths(
        root,
        root / "profile.yaml",
        root / "events.jsonl",
        root / "submissions",
        root / "materials",
        root / "interviews",
    )


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
    ensure_profile_path_is_safe(
        repo_root, paths.root.name, paths.profile_file, must_exist=True
    )
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


def _ensure_profile_subdirectories(repo_root: Path, paths: ProfilePaths) -> None:
    """Add missing layout directories without rewriting Profile facts."""

    for name in PROFILE_SUBDIRECTORIES:
        directory = paths.root / name
        ensure_profile_path_is_safe(repo_root, paths.root.name, directory)
        if directory.exists():
            if not directory.is_dir() or _is_obvious_link(directory):
                raise WorkspaceError(f"profile subdirectory is invalid: {name}")
            continue
        directory.mkdir()
        ensure_profile_path_is_safe(
            repo_root, paths.root.name, directory, must_exist=True
        )


def init_profile(repo_root: Path, profile_id: str, track_ids: tuple[str, ...] | None = None) -> InitResult:
    paths = profile_paths(repo_root, profile_id)
    ensure_profile_is_ignored(repo_root, profile_id)
    ensure_profile_path_is_safe(repo_root, profile_id, paths.root)
    if paths.root.exists():
        if not paths.root.is_dir():
            raise WorkspaceError("profile path exists and is not a directory")
        load_profile(paths, repo_root)
        read_events(paths.events_file, event_schema_path(repo_root))
        _ensure_profile_subdirectories(repo_root, paths)
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
    ensure_profile_path_is_safe(repo_root, profile_id, paths.root, must_exist=True)
    _ensure_profile_subdirectories(repo_root, paths)
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


def ensure_profile_path_is_safe(
    repo_root: Path,
    profile_id: str,
    candidate: Path | None = None,
    *,
    must_exist: bool = False,
) -> Path:
    """Validate one lexical path inside an unlinked repository-local Profile.

    This prevents accidental traversal through symlinks and Windows reparse
    points.  It is a path-integrity check for trusted local use, not a sandbox
    for hostile code.
    """

    repository = repo_root.resolve()
    profiles_root = repository / "workspace/profiles"
    profile_root = profiles_root / validate_profile_id(profile_id)
    target = (candidate or profile_root).absolute()
    try:
        profile_root.absolute().relative_to(profiles_root.absolute())
        target.relative_to(profile_root.absolute())
    except ValueError as error:
        raise WorkspaceError("Profile path is outside workspace/profiles") from error

    if not profiles_root.is_dir() or _is_obvious_link(profiles_root):
        raise WorkspaceError("workspace/profiles must be a regular, unlinked directory")

    current = profiles_root
    relative = target.relative_to(profiles_root)
    for part in relative.parts:
        current = current / part
        if _is_obvious_link(current):
            raise WorkspaceError("Profile path must not use a symlink or reparse point")
        if current.exists() and current != target and not current.is_dir():
            raise WorkspaceError("Profile path contains a non-directory component")

    if must_exist and not target.exists():
        raise WorkspaceError("required Profile path is missing")

    try:
        resolved_profiles = profiles_root.resolve(strict=True)
        if profile_root.exists():
            resolved_profile = profile_root.resolve(strict=True)
            resolved_profile.relative_to(resolved_profiles)
        else:
            resolved_profile = profile_root

        if target.exists():
            resolved_target = target.resolve(strict=True)
            if profile_root.exists():
                resolved_target.relative_to(resolved_profile)
        else:
            parent = target.parent
            while not parent.exists() and parent != profile_root.parent:
                parent = parent.parent
            resolved_parent = parent.resolve(strict=True)
            if profile_root.exists():
                resolved_parent.relative_to(resolved_profile)
            else:
                resolved_parent.relative_to(resolved_profiles)
    except (OSError, ValueError) as error:
        raise WorkspaceError("Profile path escapes workspace/profiles") from error
    return target


def _create_attempt(repo_root: Path, profile_id: str, problem: "Problem", attempt_id: str, retention_stage: str | None) -> StartResult:
    paths = profile_paths(repo_root, profile_id)
    attempt_dir = paths.submissions_root / problem.id / attempt_id
    submission_path = attempt_dir / "submission.py"
    if attempt_dir.exists():
        raise WorkspaceError("submission path already exists without a matching event")
    if not problem.ready or problem.problem_dir is None:
        raise WorkspaceError("planned problem cannot be started")
    variant = problem.retention_variant(repo_root, retention_stage) if retention_stage else None
    starter = variant[0] if variant else problem.problem_dir / "starter.py"
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
        metadata = problem.raw["retention"][retention_stage]
        payload.update({
            "retention_stage": retention_stage,
            "retention_verified": True,
            "variant_contract": metadata["description"],
        })
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
    if problem.retention_variant(repo_root, stage) is None:
        raise WorkspaceError(f"mastery blocked: verified {stage} retention assets unavailable")
    if (
        stage == "d2" and problem.id in state.retained_d2
    ) or (
        stage == "d7" and problem.id in state.retained_d7
    ):
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
