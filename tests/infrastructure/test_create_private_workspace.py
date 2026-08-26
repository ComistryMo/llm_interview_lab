from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

import pytest

from scripts.create_private_workspace import WorkspaceError, create_private_workspace
from scripts.validate_state import validate_repository_state


pytestmark = [pytest.mark.infrastructure]


def _git(repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write(root: Path, relative: str, text: str) -> None:
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_repository(tmp_path: Path) -> Path:
    source = tmp_path / "public-source"
    source.mkdir()
    files = {
        "README.md": "# Public source\n",
        "AGENTS.md": "# Rules\n",
        "pyproject.toml": "[project]\nname='fixture'\nversion='0.0.0'\n",
        "src/stage00/hard_sample_miner.py": "LEARNER_PARTIAL = True\n",
        "templates/starter/src/stage00/hard_sample_miner.py": (
            "def count_wrong_predictions(label: int, predictions: list[int]) -> int:\n"
            "    raise NotImplementedError('TODO')\n"
        ),
        "templates/LEARNER_PROFILE.md": "# Private Learner Profile\n",
        "templates/HANDOFF.md": "# Private Handoff\n",
        "state/CURRENT_TASK.md": "old fixture\n",
        "state/TASK_LEDGER.jsonl": "old fixture\n",
        "state/LEARNER_PROFILE.md": "old fixture\n",
        "state/HANDOFF.md": "old fixture\n",
        "state/PROGRESS.md": "old fixture\n",
        "state/MISTAKE_LOG.md": "old fixture\n",
        "config/export/handoff.json": "{}\n",
        "reviews/TASK_00A1_REVIEW_2026-08-26.md": "fixture review\n",
        "progress/test_runs/2026-08-26_task00a1.txt": "fixture output\n",
    }
    for relative, text in files.items():
        _write(source, relative, text)

    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "Workspace Test")
    _git(source, "config", "user.email", "workspace-test@example.invalid")
    _git(source, "add", "--all")
    _git(source, "commit", "-m", "public fixture")
    return source


def test_creates_answer_free_valid_private_workspace(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    target = tmp_path / "private-workspace"
    recorded_at = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)

    created = create_private_workspace(
        source_root=source,
        target=target,
        recorded_at=recorded_at,
    )

    assert created == target
    assert (target / ".git").exists()
    starter = (target / "src/stage00/hard_sample_miner.py").read_text(
        encoding="utf-8"
    )
    assert "NotImplementedError" in starter
    assert "LEARNER_PARTIAL" not in starter
    assert "LEARNER_PARTIAL" in (
        source / "src/stage00/hard_sample_miner.py"
    ).read_text(encoding="utf-8")
    assert not (target / "reviews/TASK_00A1_REVIEW_2026-08-26.md").exists()
    assert not (target / "progress/test_runs/2026-08-26_task00a1.txt").exists()

    _, _, snapshot = validate_repository_state(
        repo_root=target,
        ledger_path=target / "state/TASK_LEDGER.jsonl",
        current_task_path=target / "state/CURRENT_TASK.md",
    )
    assert snapshot.status.value == "not_started"
    assert snapshot.assistance_level.value == "H0"
    assert snapshot.recorded_at == recorded_at

    assert _git(target, "remote", "get-url", "upstream").stdout.decode().strip() == (
        "https://github.com/ComistryMo/llm_interview_lab.git"
    )
    assert _git(target, "remote", "get-url", "--push", "upstream").stdout.decode().strip() == "DISABLED"
    upstream = _git(
        target,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )
    assert upstream.returncode != 0
    assert _git(target, "status", "--porcelain=v1").stdout


def test_refuses_existing_or_nested_target(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    existing = tmp_path / "already-there"
    existing.mkdir()

    with pytest.raises(WorkspaceError, match="already exists"):
        create_private_workspace(source_root=source, target=existing)

    with pytest.raises(WorkspaceError, match="outside"):
        create_private_workspace(source_root=source, target=source / "private-copy")


def test_refuses_source_with_tracked_changes(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    (source / "README.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(WorkspaceError, match="tracked changes"):
        create_private_workspace(
            source_root=source,
            target=tmp_path / "private-workspace",
        )
