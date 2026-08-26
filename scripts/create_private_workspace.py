"""Create a private learner workspace from the committed public baseline.

The source checkout is never modified. The command clones its committed HEAD
into a new sibling directory, keeps the public repository as ``upstream``,
and replaces the maintainer fixture with an answer-free Stage 00 starter.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validate_state import validate_repository_state  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_UPSTREAM_URL = "https://github.com/ComistryMo/llm_interview_lab.git"
STARTER_SOURCE = "templates/starter/src/stage00/hard_sample_miner.py"

FIXTURE_FILES = (
    "progress/test_runs/2026-08-26_task00a1.txt",
    "reviews/TASK_00A1_REVIEW_2026-08-26.md",
)


class WorkspaceError(RuntimeError):
    """Raised when creating a workspace would be unsafe or ambiguous."""


def _run_git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise WorkspaceError("Git is required to create a workspace") from error
    if result.returncode != 0:
        raise WorkspaceError(f"Git command failed: {' '.join(arguments[:2])}")
    return result


def _validate_source_checkout(source_root: Path) -> Path:
    try:
        source = source_root.resolve(strict=True)
    except OSError as error:
        raise WorkspaceError("source repository cannot be resolved") from error
    if not source.is_dir() or not (source / ".git").exists():
        raise WorkspaceError("source must be a Git checkout")
    _run_git(source, "rev-parse", "--verify", "HEAD")
    status = _run_git(
        source,
        "status",
        "--porcelain=v1",
        "--untracked-files=no",
    ).stdout
    if status:
        raise WorkspaceError(
            "source has tracked changes; commit, stash, or use a clean clone first"
        )
    return source


def _is_link_or_reparse(path: Path) -> bool:
    try:
        file_stat = os.lstat(path)
    except OSError as error:
        raise WorkspaceError(f"cannot inspect generated path: {path.name}") from error
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(file_stat, "st_file_attributes", 0)
    return stat.S_ISLNK(file_stat.st_mode) or bool(attributes & reparse_flag)


def _validate_target(source: Path, target: Path) -> Path:
    target_candidate = target if target.is_absolute() else Path.cwd() / target
    target_absolute = target_candidate.resolve(strict=False)
    if target_absolute.exists():
        raise WorkspaceError("target already exists; refusing to overwrite it")
    if target_absolute == source or source in target_absolute.parents:
        raise WorkspaceError("target must be outside the public source checkout")
    parent = target_absolute.parent
    if not parent.is_dir() or _is_link_or_reparse(parent):
        raise WorkspaceError("target parent must be an existing regular directory")
    return target_absolute


def _timestamp(value: datetime | None) -> datetime:
    recorded_at = value or datetime.now().astimezone()
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise WorkspaceError("recorded_at must include a known timezone")
    return recorded_at


def _write_text(root: Path, relative: str, content: str) -> None:
    destination = root.joinpath(*relative.split("/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content.encode("utf-8"))


def _copy_template(root: Path, template: str, destination: str) -> None:
    source = root.joinpath(*template.split("/"))
    if not source.is_file() or _is_link_or_reparse(source):
        raise WorkspaceError(f"required starter template is missing: {template}")
    target = root.joinpath(*destination.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def _starter_ledger(recorded_at: datetime) -> str:
    event = {
        "schema_version": 1,
        "event_id": "evt-00A-1-registered-001",
        "task_id": "00A-1",
        "attempt_id": None,
        "event_type": "task_registered",
        "recorded_on": None,
        "recorded_at": recorded_at.isoformat(timespec="seconds"),
        "status_before": None,
        "status_after": "not_started",
        "assistance": {"level": "H0", "demonstration_only": False},
        "variant_id": None,
        "evidence": {
            "summary": "Registered the first answer-free Stage 00 task.",
            "artifacts": [],
            "test_result": "not_run",
            "oral_passed": None,
        },
        "reason": "Initialize an independent private learner workspace.",
    }
    return json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _starter_current_task() -> str:
    state = {
        "schema_version": 1,
        "task_id": "00A-1",
        "status": "not_started",
        "latest_event_id": "evt-00A-1-registered-001",
        "attempt_id": None,
        "assistance_level": "H0",
        "demonstration_only": False,
        "requires_independent_variant": False,
    }
    state_json = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"""# Current Task

<!-- CURRENT_TASK_STATE
{state_json}
END_CURRENT_TASK_STATE -->

## 当前唯一任务

- Task：00A-1 `count_wrong_predictions`；
- 状态：`not_started`；
- 任务卡：`curriculum/stage00/TASK_00A1.md`；
- 初始帮助上限：H2；
- 当前没有任何实现、review 或 retention 证据。

## 开始前

先说明输入、输出、边界和预期复杂度，再开始独立实现。不要进入 00A-2。

## 定向测试

```bash
python -m pytest tests/stage00/test_task_00a1.py -q
```

首次失败是 starter 的预期反馈；默认仓库健康测试仍应全绿。
"""


def _starter_progress() -> str:
    return """# Progress

尚无已验收 attempt。状态历史以 `state/TASK_LEDGER.jsonl` 为准。

## Gate

- Gate 0：进行中；
- 后续 Gate：未解锁。
"""


def _starter_mistakes() -> str:
    return """# Mistake Log

只记录在真实任务中出现、并有防复发规则的错误。尚无记录。
"""


def _starter_allowlist() -> str:
    policy = {
        "schema_version": 1,
        "files": [
            "AGENTS.md",
            "README.md",
            "curriculum/stage00/TASK_00A1.md",
            "docs/COACHING_PROTOCOL.md",
            "prompts/HANDOFF_FOR_EXTERNAL_REVIEW.md",
            "pyproject.toml",
            "requirements.txt",
            "src/stage00/hard_sample_miner.py",
            "state/CURRENT_TASK.md",
            "state/HANDOFF.md",
            "state/MISTAKE_LOG.md",
            "state/PROGRESS.md",
            "tests/stage00/test_task_00a1.py",
        ],
    }
    return json.dumps(policy, ensure_ascii=False, indent=2) + "\n"


def _replace_fixture(workspace: Path, recorded_at: datetime) -> None:
    for relative in FIXTURE_FILES:
        candidate = workspace.joinpath(*relative.split("/"))
        if candidate.exists():
            if _is_link_or_reparse(candidate) or not candidate.is_file():
                raise WorkspaceError(f"fixture path is not a regular file: {relative}")
            candidate.unlink()

    _copy_template(workspace, STARTER_SOURCE, "src/stage00/hard_sample_miner.py")
    _copy_template(workspace, "templates/LEARNER_PROFILE.md", "state/LEARNER_PROFILE.md")
    _copy_template(workspace, "templates/HANDOFF.md", "state/HANDOFF.md")
    _write_text(workspace, "state/TASK_LEDGER.jsonl", _starter_ledger(recorded_at))
    _write_text(workspace, "state/CURRENT_TASK.md", _starter_current_task())
    _write_text(workspace, "state/PROGRESS.md", _starter_progress())
    _write_text(workspace, "state/MISTAKE_LOG.md", _starter_mistakes())
    _write_text(workspace, "config/export/handoff.json", _starter_allowlist())


def create_private_workspace(
    *,
    source_root: Path,
    target: Path,
    recorded_at: datetime | None = None,
) -> Path:
    """Clone committed public HEAD and replace the maintainer fixture safely."""

    source = _validate_source_checkout(source_root)
    destination = _validate_target(source, target)
    timestamp = _timestamp(recorded_at)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    completed = False
    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--no-hardlinks",
                "--quiet",
                str(source),
                str(temporary),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise WorkspaceError("Git could not clone the committed public baseline")
        _run_git(temporary, "remote", "rename", "origin", "upstream")
        _run_git(temporary, "remote", "set-url", "upstream", PUBLIC_UPSTREAM_URL)
        _run_git(temporary, "remote", "set-url", "--push", "upstream", "DISABLED")
        _run_git(temporary, "branch", "--unset-upstream")
        _replace_fixture(temporary, timestamp)
        validate_repository_state(
            repo_root=temporary,
            ledger_path=temporary / "state" / "TASK_LEDGER.jsonl",
            current_task_path=temporary / "state" / "CURRENT_TASK.md",
        )
        os.replace(temporary, destination)
        completed = True
        return destination
    except WorkspaceError:
        raise
    except (OSError, ValueError) as error:
        raise WorkspaceError("workspace initialization failed") from error
    finally:
        if not completed and temporary.exists():
            # temporary was created by this function in the validated parent.
            shutil.rmtree(temporary)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="new directory outside this checkout")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate source and target without creating a workspace",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        source = _validate_source_checkout(REPO_ROOT)
        target = _validate_target(source, args.target)
        if args.dry_run:
            print("Workspace dry run passed; no directory was created.")
            print(f"Target name: {target.name}")
            return 0
        created = create_private_workspace(source_root=source, target=target)
        print(f"Created private-workspace starter: {created.name}")
        print("No origin remote was added. Confirm a private remote before personalizing.")
        print("The public repository is configured as upstream.")
        return 0
    except WorkspaceError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
