from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.cli import main
from llm_interview_lab.events import append_event, read_events, reduce_events
from llm_interview_lab.lifecycle import ReviewInput, record_review
from llm_interview_lab.workspace import event_schema_path, profile_paths


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _cli_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    shutil.copy2(REPO_ROOT / "pyproject.toml", root / "pyproject.toml")
    shutil.copy2(REPO_ROOT / ".gitignore", root / ".gitignore")
    shutil.copytree(REPO_ROOT / "curriculum" / "schema", root / "curriculum" / "schema")
    shutil.copytree(REPO_ROOT / "curriculum" / "catalog", root / "curriculum" / "catalog")
    shutil.copytree(
        REPO_ROOT / "curriculum" / "problems",
        root / "curriculum" / "problems",
    )
    shutil.copytree(REPO_ROOT / "curriculum" / "retention", root / "curriculum" / "retention")
    for name in ("schema", "templates", "demo"):
        shutil.copytree(REPO_ROOT / "workspace" / name, root / "workspace" / name)
    profiles = root / "workspace" / "profiles"
    profiles.mkdir()
    (profiles / ".gitkeep").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def test_cli_runs_answer_free_start_and_failure_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cli_repo(tmp_path)
    monkeypatch.chdir(root)

    assert main(["doctor"]) == 0
    assert main(["init", "--profile", "learner-one"]) == 0
    assert main(["next", "--profile", "learner-one"]) == 0
    assert main(["show", "FND-001"]) == 0
    assert main(["start", "FND-001", "--profile", "learner-one"]) == 0
    submission = profile_paths(root, "learner-one").submissions_root / (
        "FND-001/attempt-0001/submission.py"
    )
    original = submission.read_bytes()
    assert main(["start", "FND-001", "--profile", "learner-one"]) == 0
    assert submission.read_bytes() == original

    assert main(["test", "FND-001", "--profile", "learner-one"]) == 1
    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 1
    output = capsys.readouterr().out
    assert "MASTERY: NOT YET" in output

    events = read_events(
        profile_paths(root, "learner-one").events_file,
        event_schema_path(root),
    )
    test_event = next(event for event in events if event["event_type"] == "public_tests_run")
    assert test_event["payload"]["status"] == "failed"
    assert not any(":\\" in str(event["payload"]) for event in events)


def test_submit_requires_passing_evidence_for_current_sha_and_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _cli_repo(tmp_path)
    monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"])
    main(["start", "FND-001", "--profile", "learner-one"])
    paths = profile_paths(root, "learner-one")
    submission = paths.submissions_root / "FND-001" / "attempt-0001" / "submission.py"
    digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id="learner-one",
        event_type="public_tests_run",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={
            "submission_sha256": digest,
            "exit_code": 0,
            "status": "passed",
            "passed": 1,
            "failed": 0,
            "duration_ms": 1,
        },
    )

    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 0
    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 0
    assert main(["start", "FND-001", "--profile", "learner-one"]) == 2

    events = read_events(paths.events_file, event_schema_path(root))
    assert sum(event["event_type"] == "task_implemented" for event in events) == 1


def test_submit_rejects_passing_evidence_for_a_stale_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _cli_repo(tmp_path)
    monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"])
    main(["start", "FND-001", "--profile", "learner-one"])
    paths = profile_paths(root, "learner-one")
    submission = paths.submissions_root / "FND-001" / "attempt-0001" / "submission.py"
    original_digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id="learner-one",
        event_type="public_tests_run",
        problem_id="FND-001",
        attempt_id="attempt-0001",
        payload={
            "submission_sha256": original_digest,
            "exit_code": 0,
            "status": "passed",
            "passed": 6,
            "failed": 0,
            "duration_ms": 1,
        },
    )
    submission.write_text(submission.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 1
    state = reduce_events(read_events(paths.events_file, event_schema_path(root)))
    assert state.problem_status("FND-001") == "in_progress"


def _append_passing_evidence(root: Path, profile_id: str, attempt_id: str) -> None:
    paths = profile_paths(root, profile_id)
    submission = paths.submissions_root / "FND-001" / attempt_id / "submission.py"
    digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    append_event(
        paths.events_file,
        event_schema_path(root),
        profile_id=profile_id,
        event_type="public_tests_run",
        problem_id="FND-001",
        attempt_id=attempt_id,
        payload={
            "submission_sha256": digest,
            "exit_code": 0,
            "status": "passed",
            "passed": 6,
            "failed": 0,
            "duration_ms": 1,
        },
    )


def _review_arguments(profile_id: str) -> list[str]:
    return [
        "review",
        "FND-001",
        "--profile",
        profile_id,
        "--contract",
        "passed",
        "--oral",
        "passed",
        "--explanation",
        "Explains the contract and each branch.",
        "--complexity",
        "Linear time and constant auxiliary space.",
        "--boundaries",
        "Covers empty and invalid inputs without mutation.",
    ]


def test_two_profiles_are_independent_and_mastery_unlocks_the_next_node(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cli_repo(tmp_path)
    monkeypatch.chdir(root)
    assert main(["init", "--profile", "learner-one", "--track", "ai_foundation"]) == 0
    assert main(["init", "--profile", "learner-two", "--track", "ai_foundation"]) == 0
    assert main(["start", "FND-001", "--profile", "learner-one"]) == 0
    _append_passing_evidence(root, "learner-one", "attempt-0001")
    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 0

    reviewed_at = datetime.now(timezone.utc) - timedelta(days=8)
    result = record_review(
        root,
        "learner-one",
        "FND-001",
        ReviewInput(
            "passed",
            "passed",
            "Explains the contract and each branch.",
            "Linear time and constant auxiliary space.",
            "Covers empty and invalid inputs without mutation.",
        ),
        timestamp=reviewed_at,
    )
    assert result.status == "reviewed"

    assert main(["retain", "FND-001", "--stage", "d2", "--profile", "learner-one"]) == 0
    _append_passing_evidence(root, "learner-one", "attempt-0002")
    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 0
    assert main(_review_arguments("learner-one")) == 0

    assert main(["retain", "FND-001", "--stage", "d7", "--profile", "learner-one"]) == 0
    _append_passing_evidence(root, "learner-one", "attempt-0003")
    assert main(["submit", "FND-001", "--profile", "learner-one"]) == 0
    assert main(_review_arguments("learner-one")) == 0

    learner_one = reduce_events(
        read_events(
            profile_paths(root, "learner-one").events_file,
            event_schema_path(root),
        )
    )
    learner_two = reduce_events(
        read_events(
            profile_paths(root, "learner-two").events_file,
            event_schema_path(root),
        )
    )
    assert learner_one.problem_status("FND-001") == "mastered"
    assert learner_two.problem_status("FND-001") == "not_started"

    assert main(["next", "--profile", "learner-one"]) == 0
    output = capsys.readouterr().out
    assert "FND-002 Sample Contract Validation" in output
    assert main(["start", "FND-002", "--profile", "learner-one"]) == 0


def test_next_reports_mastery_blocked_without_verified_retention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cli_repo(tmp_path)
    monkeypatch.chdir(root)
    main(["init", "--profile", "learner-one"])
    paths = profile_paths(root, "learner-one")
    attempt_dir = paths.submissions_root / "FND-002" / "attempt-0001"
    attempt_dir.mkdir(parents=True)
    submission = attempt_dir / "submission.py"
    submission.write_text("def validate_sample(sample): return sample\n", encoding="utf-8")
    digest = hashlib.sha256(submission.read_bytes()).hexdigest()
    schema = event_schema_path(root)
    append_event(paths.events_file, schema, profile_id="learner-one", event_type="task_started", problem_id="FND-002", attempt_id="attempt-0001", payload={"submission_relpath": submission.relative_to(root).as_posix()})
    append_event(paths.events_file, schema, profile_id="learner-one", event_type="task_implemented", problem_id="FND-002", attempt_id="attempt-0001", payload={"submission_sha256": digest})
    record_review(root, "learner-one", "FND-002", ReviewInput("passed", "passed", "Explains validation.", "Linear time.", "Covers invalid fields."), timestamp=datetime.now(timezone.utc) - timedelta(days=8))

    assert main(["next", "--profile", "learner-one"]) == 0
    output = capsys.readouterr().out
    assert "MASTERY BLOCKED" in output
    assert "FND-002 verified retention assets unavailable" in output
