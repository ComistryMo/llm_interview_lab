"""Repository-local workspace paths, profile initialization, and attempts."""

from __future__ import annotations

from dataclasses import dataclass
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
)


class WorkspaceError(RuntimeError):
    """Raised for an invalid or unsafe local workspace operation."""


@dataclass(frozen=True)
class ProfilePaths:
    """Resolved paths for one repository-local profile."""

    root: Path
    profile_file: Path
    events_file: Path
    submissions_root: Path


@dataclass(frozen=True)
class InitResult:
    """Profile initialization result."""

    paths: ProfilePaths
    created: bool


@dataclass(frozen=True)
class StartResult:
    """Problem start result, including idempotent reuse."""

    attempt_id: str
    submission_path: Path
    created: bool


def find_repository_root(start: Path | None = None) -> Path:
    """Find the clone root; global/out-of-repository use is unsupported."""

    candidate = (start or Path.cwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (
            (directory / "pyproject.toml").is_file()
            and (directory / "curriculum").is_dir()
            and (directory / "workspace").is_dir()
        ):
            return directory
    raise WorkspaceError("run llm-lab inside a cloned llm_interview_lab repository")


def validate_profile_id(profile_id: str) -> str:
    """Return a safe profile ID or raise a stable error."""

    if PROFILE_ID_RE.fullmatch(profile_id) is None:
        raise WorkspaceError(
            "profile ID must start with a lowercase letter and contain only "
            "lowercase letters, digits, or hyphens"
        )
    return profile_id


def profile_paths(repo_root: Path, profile_id: str) -> ProfilePaths:
    """Build paths without creating a profile."""

    valid_id = validate_profile_id(profile_id)
    root = repo_root / "workspace" / "profiles" / valid_id
    return ProfilePaths(
        root=root,
        profile_file=root / "profile.yaml",
        events_file=root / "events.jsonl",
        submissions_root=root / "submissions",
    )


def event_schema_path(repo_root: Path) -> Path:
    return repo_root / "workspace" / "schema" / "event.schema.json"


def profile_schema_path(repo_root: Path) -> Path:
    return repo_root / "workspace" / "schema" / "profile.schema.json"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise WorkspaceError(f"{label} cannot be read") from error
    if not isinstance(value, dict):
        raise WorkspaceError(f"{label} must be an object")
    return value


def validate_profile_data(data: Any, repo_root: Path) -> dict[str, Any]:
    """Validate parsed profile data against the public schema."""

    if not isinstance(data, dict):
        raise WorkspaceError("profile.yaml must contain an object")
    schema = _load_json(profile_schema_path(repo_root), "profile schema")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda item: list(item.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "<root>"
        raise WorkspaceError(f"invalid profile at {location}: {errors[0].message}")
    return data


def load_profile(paths: ProfilePaths, repo_root: Path) -> dict[str, Any]:
    """Load one existing profile without enumerating other profiles."""

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
    result = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", relative],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode not in {0, 1}:
        raise WorkspaceError("Git ignore check could not be completed")
    return result.returncode == 0


def ensure_profile_is_ignored(repo_root: Path, profile_id: str) -> None:
    """Fail closed before writing any real profile data."""

    paths = profile_paths(repo_root, profile_id)
    if not _git_path_is_ignored(repo_root, paths.events_file):
        raise WorkspaceError("workspace profile path is not ignored by Git")


def init_profile(repo_root: Path, profile_id: str) -> InitResult:
    """Create an answer-free profile, or return an existing valid one."""

    paths = profile_paths(repo_root, profile_id)
    ensure_profile_is_ignored(repo_root, profile_id)
    if paths.root.exists():
        if not paths.root.is_dir():
            raise WorkspaceError("profile path exists and is not a directory")
        load_profile(paths, repo_root)
        read_events(paths.events_file, event_schema_path(repo_root))
        return InitResult(paths=paths, created=False)

    template_path = repo_root / "workspace" / "templates" / "default" / "profile.yaml"
    try:
        template = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise WorkspaceError("default profile template cannot be read") from error
    if not isinstance(template, dict):
        raise WorkspaceError("default profile template must be an object")
    template["profile_id"] = profile_id
    template["synthetic"] = False
    validate_profile_data(template, repo_root)

    paths.root.mkdir(parents=True, exist_ok=False)
    for name in PROFILE_SUBDIRECTORIES:
        (paths.root / name).mkdir()
    paths.profile_file.write_text(
        yaml.safe_dump(template, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    append_event(
        paths.events_file,
        event_schema_path(repo_root),
        profile_id=profile_id,
        event_type="profile_created",
        problem_id=None,
        attempt_id=None,
        payload={"synthetic": False},
    )
    return InitResult(paths=paths, created=True)


def load_workspace_state(repo_root: Path, profile_id: str) -> WorkspaceState:
    """Load one explicit profile and reduce its events."""

    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    return reduce_events(read_events(paths.events_file, event_schema_path(repo_root)))


def _is_obvious_link(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def start_problem(
    repo_root: Path,
    profile_id: str,
    problem: "Problem",
) -> StartResult:
    """Start attempt-0001 without ever overwriting an existing submission."""

    paths = profile_paths(repo_root, profile_id)
    load_profile(paths, repo_root)
    events = read_events(paths.events_file, event_schema_path(repo_root))
    state = reduce_events(events)
    matching = [
        attempt
        for (candidate, _), attempt in state.attempts.items()
        if candidate == problem.id
    ]
    if any(attempt.implemented for attempt in matching):
        raise WorkspaceError("problem is already implemented; --new-attempt is not available")
    if matching:
        attempt = matching[-1]
        if attempt.submission_relpath is None:
            raise WorkspaceError("existing attempt has no submission path")
        existing = repo_root / Path(attempt.submission_relpath)
        if not existing.is_file():
            raise WorkspaceError("existing attempt submission is missing")
        return StartResult(
            attempt_id=attempt.attempt_id,
            submission_path=existing,
            created=False,
        )

    attempt_id = "attempt-0001"
    attempt_dir = paths.submissions_root / problem.id / attempt_id
    submission_path = attempt_dir / "submission.py"
    if attempt_dir.exists() or submission_path.exists():
        raise WorkspaceError("submission path already exists without a matching event")

    starter = problem.problem_dir / "starter.py"
    if not starter.is_file() or _is_obvious_link(starter):
        raise WorkspaceError("problem starter is missing or unsafe")
    starter_bytes = starter.read_bytes()
    attempt_dir.mkdir(parents=True, exist_ok=False)
    submission_path.write_bytes(starter_bytes)
    relative = submission_path.relative_to(repo_root).as_posix()
    append_event(
        paths.events_file,
        event_schema_path(repo_root),
        profile_id=profile_id,
        event_type="task_started",
        problem_id=problem.id,
        attempt_id=attempt_id,
        payload={
            "submission_relpath": relative,
            "starter_sha256": hashlib.sha256(starter_bytes).hexdigest(),
        },
    )
    return StartResult(
        attempt_id=attempt_id,
        submission_path=submission_path,
        created=True,
    )
