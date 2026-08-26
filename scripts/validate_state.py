"""Validate the append-only task ledger and CURRENT_TASK snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.state_model import (  # noqa: E402
    StateValidationError,
    TaskSnapshot,
    load_ledger,
    parse_current_task_state,
    replay_events,
    validate_append_only,
    validate_artifacts,
    validate_current_task,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = REPO_ROOT / "state" / "TASK_LEDGER.jsonl"
DEFAULT_CURRENT_TASK = REPO_ROOT / "state" / "CURRENT_TASK.md"


def validate_repository_state(
    *,
    repo_root: Path,
    ledger_path: Path,
    current_task_path: Path,
    base_ledger_path: Path | None = None,
) -> tuple[int, int, TaskSnapshot]:
    """Validate all state files and return event/task counts and current snapshot."""

    try:
        events = load_ledger(ledger_path)
        snapshots = replay_events(events)
        validate_artifacts(events, repo_root=repo_root)
        current_markdown = current_task_path.read_text(encoding="utf-8")
        current = parse_current_task_state(current_markdown)
        snapshot = validate_current_task(current, snapshots)

        if base_ledger_path is not None:
            base = base_ledger_path.read_bytes()
            active = ledger_path.read_bytes()
            validate_append_only(base=base, current=active)
    except StateValidationError:
        raise
    except (OSError, UnicodeError) as error:
        # Keep CLI/JSON output shareable: exception strings frequently contain
        # user names and absolute paths on both Windows and POSIX systems.
        raise StateValidationError(
            "cannot access required repository state files as UTF-8"
        ) from error

    return len(events), len(snapshots), snapshot


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--current-task", type=Path, default=DEFAULT_CURRENT_TASK)
    parser.add_argument(
        "--base-ledger",
        type=Path,
        help="optional previous ledger copy used to enforce append-only history",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        event_count, task_count, snapshot = validate_repository_state(
            repo_root=args.repo_root,
            ledger_path=args.ledger,
            current_task_path=args.current_task,
            base_ledger_path=args.base_ledger,
        )
    except StateValidationError as error:
        if args.json:
            print(
                json.dumps(
                    {"schema_version": 1, "ok": False, "error": str(error)},
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            print(f"STATE INVALID: {error}", file=sys.stderr)
        return 1

    result = {
        "schema_version": 1,
        "ok": True,
        "event_count": event_count,
        "task_count": task_count,
        "current_task": {
            "task_id": snapshot.task_id,
            "status": snapshot.status.value,
            "latest_event_id": snapshot.latest_event_id,
            "attempt_id": snapshot.attempt_id,
            "assistance_level": snapshot.assistance_level.value,
            "demonstration_only": snapshot.demonstration_only,
            "requires_independent_variant": snapshot.requires_independent_variant,
        },
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        current = result["current_task"]
        print(
            "STATE VALID: "
            f"{event_count} event(s), {task_count} task(s), "
            f"current={current['task_id']}:{current['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
