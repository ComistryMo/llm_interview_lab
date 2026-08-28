from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
from llm_interview_lab.lifecycle import ReviewInput, record_review
from llm_interview_lab.workspace import (
    WorkspaceError,
    event_schema_path,
    init_profile,
    profile_paths,
    start_problem,
    start_retention,
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


def _starter_problem(root: Path, problem_id: str = "FND-001") -> Problem:
    problem_dir = root / "curriculum" / "problems" / f"{problem_id}-test"
    problem_dir.mkdir(parents=True)
    (problem_dir / "starter.py").write_text(
        "def count_wrong_predictions(label, predictions):\n"
        "    raise NotImplementedError\n",
        encoding="utf-8",
    )
    retention: dict[str, object] = {}
    for stage, symbol in (("d2", "wrong_rate"), ("d7", "wrong_indices")):
        variant = root / "curriculum" / "retention" / problem_id / stage
        variant.mkdir(parents=True)
        (variant / "starter.py").write_text(
            f"def {symbol}(*args, **kwargs):\n    raise NotImplementedError\n",
            encoding="utf-8",
        )
        (variant / "test_public.py").write_text("def test_placeholder(submission):\n    assert submission\n", encoding="utf-8")
        retention[stage] = {
            "description": f"verified {stage} variant",
            "assets": {"root": f"curriculum/retention/{problem_id}/{stage}", "starter": "starter.py", "public_tests": "test_public.py"},
            "interface": {"language": "python", "framework": "stdlib", "symbol": symbol},
            "oracle_validated": True,
        }
    return Problem(
        id=problem_id,
        title="Workspace test problem",
        status="ready",
        prerequisites=(),
        problem_dir=problem_dir,
        symbol="count_wrong_predictions",
        runner_kind="pytest",
        public_tests=problem_dir / "test_public.py",
        oracle_kind="fixture_expected",
        raw={"retention": retention},
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


def test_core_workspace_refuses_a_second_active_problem(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    first = _starter_problem(root, "FND-001")
    second = _starter_problem(root, "FND-002")
    start_problem(root, "learner-one", first)

    with pytest.raises(WorkspaceError, match="finish the current implementation"):
        start_problem(root, "learner-one", second)


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


def _mark_implemented(root: Path, profile_id: str, problem_id: str, attempt_id: str, submission: Path) -> None:
    paths = profile_paths(root, profile_id)
    digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id=profile_id,
        event_type="public_tests_run",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={"submission_sha256": digest, "exit_code": 0, "status": "passed", "passed": 5, "failed": 0, "duration_ms": 1},
    )
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id=profile_id,
        event_type="task_implemented",
        problem_id=problem_id,
        attempt_id=attempt_id,
        payload={"submission_sha256": digest},
    )


def _passing_review(root: Path, profile_id: str, problem_id: str, at: datetime):
    return record_review(
        root,
        profile_id,
        problem_id,
        ReviewInput("passed", "passed", "explains every branch", "O(n) time and O(1) space", "empty and invalid inputs covered"),
        timestamp=at,
    )


def test_review_d2_d7_and_mastery_are_evidence_gated(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    problem = _starter_problem(root)
    initial = start_problem(root, "learner-one", problem)
    initial.submission_path.write_text("# independent implementation\n", encoding="utf-8")
    _mark_implemented(root, "learner-one", problem.id, initial.attempt_id, initial.submission_path)
    reviewed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _passing_review(root, "learner-one", problem.id, reviewed_at).status == "reviewed"

    d2 = start_retention(root, "learner-one", problem, "d2", now=reviewed_at + timedelta(days=2))
    assert d2.attempt_id == "attempt-0002"
    assert d2.submission_path.read_text(encoding="utf-8") != initial.submission_path.read_text(encoding="utf-8")
    _mark_implemented(root, "learner-one", problem.id, d2.attempt_id, d2.submission_path)
    assert _passing_review(root, "learner-one", problem.id, reviewed_at + timedelta(days=2)).status == "retained_d2"

    d7 = start_retention(root, "learner-one", problem, "d7", now=reviewed_at + timedelta(days=7))
    assert d7.attempt_id == "attempt-0003"
    _mark_implemented(root, "learner-one", problem.id, d7.attempt_id, d7.submission_path)
    assert _passing_review(root, "learner-one", problem.id, reviewed_at + timedelta(days=7)).mastered
    final = reduce_events(read_events(profile_paths(root, "learner-one").events_file, event_schema_path(root)))
    assert final.problem_status(problem.id) == "mastered"


def test_retention_without_verified_assets_is_blocked(tmp_path: Path) -> None:
    root = _workspace_repo(tmp_path)
    init_profile(root, "learner-one")
    problem = _starter_problem(root)
    problem.raw["retention"]["d2"] = "description only"
    initial = start_problem(root, "learner-one", problem)
    _mark_implemented(root, "learner-one", problem.id, initial.attempt_id, initial.submission_path)
    reviewed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    _passing_review(root, "learner-one", problem.id, reviewed_at)

    with pytest.raises(WorkspaceError, match="mastery blocked"):
        start_retention(root, "learner-one", problem, "d2", now=reviewed_at + timedelta(days=2))
