from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.catalog import Problem
from llm_interview_lab.events import (
    EventError,
    append_event,
    read_events,
    reduce_events,
)
from llm_interview_lab.workspace import (
    WorkspaceError,
    event_schema_path,
    init_profile,
    start_problem,
)


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _workspace_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    (root / ".gitignore").write_text(
        "/workspace/profiles/*\n!/workspace/profiles/.gitkeep\n",
        encoding="utf-8",
    )
    shutil.copytree(REPO_ROOT / "workspace" / "schema", root / "workspace" / "schema")
    shutil.copytree(
        REPO_ROOT / "workspace" / "templates",
        root / "workspace" / "templates",
    )
    profiles = root / "workspace" / "profiles"
    profiles.mkdir()
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def _starter_problem(root: Path) -> Problem:
    problem_dir = root / "curriculum" / "problems" / "FND-001-test"
    problem_dir.mkdir(parents=True)
    (problem_dir / "starter.py").write_text(
        "def count_wrong_predictions(label, predictions):\n"
        "    raise NotImplementedError\n",
        encoding="utf-8",
    )
    return Problem(
        id="FND-001",
        title="Workspace test problem",
        status="ready",
        prerequisites=(),
        problem_dir=problem_dir,
        symbol="count_wrong_predictions",
        runner_kind="pytest",
        public_tests=problem_dir / "test_public.py",
        oracle_kind="fixture_expected",
        raw={},
    )


def test_init_creates_ignored_profile_without_changing_git_status(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    before = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    result = init_profile(root, "learner-one")
    after = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert result.created
    assert result.paths.profile_file.is_file()
    assert result.paths.events_file.is_file()
    assert before == after
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "workspace/profiles/learner-one/events.jsonl"],
        cwd=root,
        check=False,
    )
    assert ignored.returncode == 0


def test_init_is_idempotent_and_does_not_replace_events(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    first = init_profile(root, "learner-one")
    original = first.paths.events_file.read_bytes()

    second = init_profile(root, "learner-one")

    assert not second.created
    assert second.paths.events_file.read_bytes() == original


def test_reducer_uses_physical_order_not_timestamp_order(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    schema = event_schema_path(root)
    append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_started",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_relpath": "workspace/profiles/learner-one/submissions/a.py"},
        timestamp=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_started",
        problem_id="FND-002",
        attempt_id="attempt-0001",
        payload={"submission_relpath": "workspace/profiles/learner-one/submissions/b.py"},
        timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )

    state = reduce_events(read_events(paths.events_file, schema))

    assert state.current_problem_id == "FND-002"


def test_public_test_event_requires_complete_path_free_evidence(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    schema = event_schema_path(root)
    append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_started",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_relpath": "workspace/profiles/learner-one/submissions/a.py"},
    )

    with pytest.raises(EventError, match="payload missing"):
        append_event(
            paths.events_file,
            schema,
            profile_id="learner-one",
            event_type="public_tests_run",
            problem_id="FND-001",
            attempt_id="attempt-0001",
            payload={"submission_sha256": "0" * 64},
        )
    with pytest.raises(EventError, match="absolute paths"):
        append_event(
            paths.events_file,
            schema,
            profile_id="learner-one",
            event_type="task_started",
            problem_id="FND-002",
            attempt_id="attempt-0001",
            payload={"submission_relpath": "C:/private/submission.py"},
        )


def test_task_implemented_is_idempotent_for_same_submission(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    schema = event_schema_path(root)
    append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_started",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_relpath": "workspace/profiles/learner-one/submissions/a.py"},
    )
    first = append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_implemented",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_sha256": "a" * 64},
    )
    second = append_event(
        paths.events_file,
        schema,
        profile_id="learner-one",
        event_type="task_implemented",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_sha256": "a" * 64},
    )

    assert first.appended
    assert not second.appended
    assert first.event == second.event
    assert sum(
        event["event_type"] == "task_implemented"
        for event in read_events(paths.events_file, schema)
    ) == 1


def test_start_reuses_unfinished_attempt_without_overwriting(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    problem = _starter_problem(root)
    first = start_problem(root, "learner-one", problem)
    first.submission_path.write_text("# learner edit\n", encoding="utf-8")

    second = start_problem(root, "learner-one", problem)

    assert first.created
    assert not second.created
    assert second.attempt_id == "attempt-0001"
    assert second.submission_path.read_text(encoding="utf-8") == "# learner edit\n"


def test_start_refuses_implemented_attempt(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    paths = init_profile(root, "learner-one").paths
    problem = _starter_problem(root)
    started = start_problem(root, "learner-one", problem)
    digest = hashlib.sha256(started.submission_path.read_bytes()).hexdigest()
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id="learner-one",
        event_type="task_implemented",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={"submission_sha256": digest},
    )

    with pytest.raises(WorkspaceError, match="already implemented"):
        start_problem(root, "learner-one", problem)
