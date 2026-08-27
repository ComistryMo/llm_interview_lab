from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess

import pytest

from llm_interview_lab.cli import main
from llm_interview_lab.events import append_event, read_events
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
    shutil.copytree(REPO_ROOT / "workspace", root / "workspace")
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
