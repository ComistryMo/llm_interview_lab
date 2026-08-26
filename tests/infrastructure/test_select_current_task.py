from __future__ import annotations

import json
import os
from pathlib import Path
import shutil

import pytest

from scripts.select_current_task import main
from scripts.state_model import load_ledger, parse_current_task_state, replay_events
from scripts.validate_state import validate_repository_state


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _private_training_repo(tmp_path: Path) -> Path:
    root = tmp_path / "private-repository"
    for directory in ("curriculum", "references", "state", "progress", "reviews"):
        shutil.copytree(REPO_ROOT / directory, root / directory)
    shutil.copytree(REPO_ROOT / "tests" / "stage00", root / "tests" / "stage00")
    return root


def _set_00a1_implemented(root: Path) -> None:
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    events = [
        {
            "schema_version": 1,
            "event_id": "evt-00A-1-attempt-002",
            "task_id": "00A-1",
            "attempt_id": "00A-1-A002",
            "event_type": "attempt_started",
            "recorded_on": None,
            "recorded_at": "2026-08-26T10:00:00+08:00",
            "status_before": "needs_revision",
            "status_after": "attempted",
            "assistance": {"level": "H1", "demonstration_only": False},
            "variant_id": None,
            "evidence": {
                "summary": "Test fixture starts a second attempt.",
                "artifacts": [],
                "test_result": "not_run",
                "oral_passed": None,
            },
            "reason": "Prepare a validated selector fixture.",
        },
        {
            "schema_version": 1,
            "event_id": "evt-00A-1-implemented-002",
            "task_id": "00A-1",
            "attempt_id": "00A-1-A002",
            "event_type": "implementation_verified",
            "recorded_on": None,
            "recorded_at": "2026-08-26T10:01:00+08:00",
            "status_before": "attempted",
            "status_after": "implemented",
            "assistance": {"level": "H1", "demonstration_only": False},
            "variant_id": None,
            "evidence": {
                "summary": "Test fixture records passing implementation evidence.",
                "artifacts": ["reviews/TASK_00A1_REVIEW_2026-08-26.md"],
                "test_result": "passed",
                "oral_passed": None,
            },
            "reason": "Prepare a validated selector fixture.",
        },
    ]
    with ledger.open("a", encoding="utf-8", newline="\n") as stream:
        for event in events:
            stream.write(
                json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    snapshot = replay_events(load_ledger(ledger))["00A-1"]
    state = {
        "schema_version": 1,
        "task_id": snapshot.task_id,
        "status": snapshot.status.value,
        "latest_event_id": snapshot.latest_event_id,
        "attempt_id": snapshot.attempt_id,
        "assistance_level": snapshot.assistance_level.value,
        "demonstration_only": snapshot.demonstration_only,
        "requires_independent_variant": snapshot.requires_independent_variant,
    }
    (root / "state" / "CURRENT_TASK.md").write_text(
        "# Current Task\n\n<!-- CURRENT_TASK_STATE\n"
        + json.dumps(state, sort_keys=True, separators=(",", ":"))
        + "\nEND_CURRENT_TASK_STATE -->\n",
        encoding="utf-8",
    )


def test_selection_is_dry_run_by_default_and_preserves_current_files(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    current = root / "state" / "CURRENT_TASK.md"
    before = (ledger.read_bytes(), current.read_bytes())

    exit_code = main(["00A-1", "--repo-root", str(root)])

    assert exit_code == 0
    assert "Dry run only" in capsys.readouterr().out
    assert (ledger.read_bytes(), current.read_bytes()) == before


def test_native_selection_does_not_depend_on_external_navigation_freshness(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)
    navigation = root / "curriculum" / "external" / "NAVIGATION.md"
    navigation.write_text("stale external navigation\n", encoding="utf-8")

    exit_code = main(["00A-1", "--repo-root", str(root)])

    assert exit_code == 0
    assert "Selection preview: 00A-1 (native)" in capsys.readouterr().out


def test_native_selection_cannot_bypass_machine_prerequisite(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)

    exit_code = main(
        [
            "00A-2",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )

    assert exit_code == 1
    assert "machine prerequisites are not satisfied" in capsys.readouterr().err
    current = parse_current_task_state(
        (root / "state" / "CURRENT_TASK.md").read_text(encoding="utf-8")
    )
    assert current.task_id == "00A-1"


def test_external_group_is_preview_only_until_machine_readiness_exists(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    current = root / "state" / "CURRENT_TASK.md"
    before = (ledger.read_bytes(), current.read_bytes())

    preview = main(
        ["EXT-CS336-A1-tokenizer-core", "--repo-root", str(root)]
    )

    assert preview == 1
    output = capsys.readouterr().out
    assert "Integration status: inventory-audited" in output
    assert "not implementation-ready" in output
    assert "Learner status scope: companion-runtime-only" in output
    assert (ledger.read_bytes(), current.read_bytes()) == before

    exit_code = main(
        [
            "EXT-CS336-A1-tokenizer-core",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )

    assert exit_code == 1
    assert "machine prerequisites are not satisfied" in capsys.readouterr().err
    assert (ledger.read_bytes(), current.read_bytes()) == before


def test_native_selection_registers_once_after_machine_prerequisite(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)
    _set_00a1_implemented(root)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    before_lines = ledger.read_text(encoding="utf-8").splitlines()

    selected = main(
        [
            "00A-2",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )

    assert selected == 0
    assert "Selected 00A-2" in capsys.readouterr().out
    after_lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(after_lines) == len(before_lines) + 1
    event = json.loads(after_lines[-1])
    assert event["task_id"] == "00A-2"
    assert event["status_after"] == "not_started"
    _, _, snapshot = validate_repository_state(
        repo_root=root,
        ledger_path=ledger,
        current_task_path=root / "state" / "CURRENT_TASK.md",
    )
    assert snapshot.task_id == "00A-2"

    ledger_before_repeat = ledger.read_bytes()
    current_before_repeat = (root / "state" / "CURRENT_TASK.md").read_bytes()
    repeat = main(
        [
            "00A-2",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
        ]
    )
    assert repeat == 0
    assert ledger.read_bytes() == ledger_before_repeat
    assert (root / "state" / "CURRENT_TASK.md").read_bytes() == current_before_repeat


def test_external_successor_reports_aggregate_and_has_no_boolean_bypass(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)

    blocked = main(
        ["EXT-CS336-A2-ddp", "--repo-root", str(root)]
    )
    assert blocked == 1
    output = capsys.readouterr().out
    assert "portable aggregate" in output
    assert "EXT-CS336-A1-tokenizer-core" in output

    refused = main(
        [
            "EXT-CS336-A2-ddp",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )
    assert refused == 1
    assert "machine prerequisites are not satisfied" in capsys.readouterr().err


def test_selection_lock_refuses_concurrent_or_stale_writer(
    tmp_path: Path,
    capsys,
) -> None:
    root = _private_training_repo(tmp_path)
    _set_00a1_implemented(root)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    current = root / "state" / "CURRENT_TASK.md"
    before = (ledger.read_bytes(), current.read_bytes())
    (root / "state" / ".task-selection.lock").write_text("held\n", encoding="utf-8")

    exit_code = main(
        [
            "00A-2",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )

    assert exit_code == 1
    assert "selection lock" in capsys.readouterr().err
    assert (ledger.read_bytes(), current.read_bytes()) == before


def test_replace_failure_rolls_back_uncommitted_registration(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    import scripts.select_current_task as selector

    root = _private_training_repo(tmp_path)
    _set_00a1_implemented(root)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    current = root / "state" / "CURRENT_TASK.md"
    before = (ledger.read_bytes(), current.read_bytes())

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise PermissionError("injected replace failure")

    monkeypatch.setattr(selector.os, "replace", fail_replace)
    exit_code = main(
        [
            "00A-2",
            "--repo-root",
            str(root),
            "--apply",
            "--acknowledge-human-gates",
            "--acknowledge-paused-current",
        ]
    )

    assert exit_code == 1
    assert "state files could not be updated safely" in capsys.readouterr().err
    assert (ledger.read_bytes(), current.read_bytes()) == before


def test_selection_refuses_hard_linked_state_file(tmp_path: Path, capsys) -> None:
    root = _private_training_repo(tmp_path)
    ledger = root / "state" / "TASK_LEDGER.jsonl"
    os.link(ledger, tmp_path / "outside-ledger.jsonl")

    exit_code = main(["00A-1", "--repo-root", str(root)])

    assert exit_code == 1
    assert "must not be hard-linked" in capsys.readouterr().err
