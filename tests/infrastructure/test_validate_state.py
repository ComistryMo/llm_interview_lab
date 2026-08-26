from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.state_model import (
    StateValidationError,
    load_ledger,
    parse_current_task_state,
    replay_events,
    validate_append_only,
)
from scripts.validate_state import main, validate_repository_state


pytestmark = pytest.mark.infrastructure
REPO_ROOT = Path(__file__).resolve().parents[2]


def _event(
    *,
    event_id: str,
    event_type: str,
    recorded_on: str,
    recorded_at: str | None = None,
    status_before: str | None,
    status_after: str,
    attempt_id: str | None,
    level: str = "H0",
    demonstration_only: bool | None = None,
    variant_id: str | None = None,
    test_result: str = "not_run",
    oral_passed: bool | None = None,
    artifacts: list[str] | None = None,
) -> dict[str, Any]:
    if demonstration_only is None:
        demonstration_only = level == "H5"
    is_legacy = event_type == "legacy_import"
    return {
        "schema_version": 1,
        "event_id": event_id,
        "task_id": "TEST-001",
        "attempt_id": attempt_id,
        "event_type": event_type,
        "recorded_on": recorded_on if is_legacy else None,
        "recorded_at": (
            None
            if is_legacy
            else recorded_at or f"{recorded_on}T00:00:00Z"
        ),
        "status_before": status_before,
        "status_after": status_after,
        "assistance": {
            "level": level,
            "demonstration_only": demonstration_only,
        },
        "variant_id": variant_id,
        "evidence": {
            "summary": f"Evidence for {event_type}",
            "artifacts": artifacts or [],
            "test_result": test_result,
            "oral_passed": oral_passed,
        },
        "reason": f"Record {event_type}",
    }


def _successful_progression(*, level: str = "H0") -> list[dict[str, Any]]:
    demonstration_only = level == "H5"
    return [
        _event(
            event_id="evt-register",
            event_type="task_registered",
            recorded_on="2026-01-01",
            status_before=None,
            status_after="not_started",
            attempt_id=None,
        ),
        _event(
            event_id="evt-attempt",
            event_type="attempt_started",
            recorded_on="2026-01-01",
            status_before="not_started",
            status_after="attempted",
            attempt_id="TEST-001-A001",
            level=level,
            demonstration_only=demonstration_only,
        ),
        _event(
            event_id="evt-implemented",
            event_type="implementation_verified",
            recorded_on="2026-01-01",
            status_before="attempted",
            status_after="implemented",
            attempt_id="TEST-001-A001",
            level=level,
            demonstration_only=demonstration_only,
            test_result="passed",
            artifacts=["proof.txt"],
        ),
        _event(
            event_id="evt-reviewed",
            event_type="review_passed",
            recorded_on="2026-01-01",
            status_before="implemented",
            status_after="reviewed",
            attempt_id="TEST-001-A001",
            level=level,
            demonstration_only=demonstration_only,
            test_result="passed",
            oral_passed=True,
            artifacts=["proof.txt"],
        ),
    ]


def _write_ledger(path: Path, events: list[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for event in events
    )
    path.write_bytes(content.encode("utf-8"))


def _state_block(
    *,
    status: str,
    latest_event_id: str,
    attempt_id: str | None,
    assistance_level: str,
    demonstration_only: bool,
    requires_independent_variant: bool = False,
) -> str:
    state = {
        "schema_version": 1,
        "task_id": "TEST-001",
        "status": status,
        "latest_event_id": latest_event_id,
        "attempt_id": attempt_id,
        "assistance_level": assistance_level,
        "demonstration_only": demonstration_only,
        "requires_independent_variant": requires_independent_variant,
    }
    return (
        "# Current Task\n\n<!-- CURRENT_TASK_STATE\n"
        + json.dumps(state, sort_keys=True, separators=(",", ":"))
        + "\nEND_CURRENT_TASK_STATE -->\n"
    )


def _parse(events: list[dict[str, Any]], tmp_path: Path) -> list[Any]:
    ledger = tmp_path / "TASK_LEDGER.jsonl"
    _write_ledger(ledger, events)
    return load_ledger(ledger)


def test_complete_legal_progression_reaches_mastered(tmp_path: Path) -> None:
    events = _successful_progression()
    events.extend(
        [
            _event(
                event_id="evt-48h",
                event_type="retention_48h_passed",
                recorded_on="2026-01-03",
                status_before="reviewed",
                status_after="retained_48h",
                attempt_id="TEST-001-R48",
                variant_id="rewrite-48h",
                test_result="passed",
                artifacts=["proof.txt"],
            ),
            _event(
                event_id="evt-7d",
                event_type="retention_7d_passed",
                recorded_on="2026-01-08",
                status_before="retained_48h",
                status_after="retained_7d",
                attempt_id="TEST-001-R7D",
                variant_id="variant-7d",
                test_result="passed",
                artifacts=["proof.txt"],
            ),
            _event(
                event_id="evt-mastered",
                event_type="mastery_passed",
                recorded_on="2026-01-22",
                status_before="retained_7d",
                status_after="mastered",
                attempt_id="TEST-001-M001",
                variant_id="mixed-21d",
                test_result="passed",
                oral_passed=True,
                artifacts=["proof.txt"],
            ),
        ]
    )

    snapshot = replay_events(_parse(events, tmp_path))["TEST-001"]

    assert snapshot.status.value == "mastered"
    assert snapshot.assistance_level.value == "H0"
    assert not snapshot.demonstration_only
    assert snapshot.used_variant_ids == {
        "rewrite-48h",
        "variant-7d",
        "mixed-21d",
    }


def test_failed_attempt_can_restart_but_cannot_skip_review(tmp_path: Path) -> None:
    events = _successful_progression()[:2]
    events.append(
        _event(
            event_id="evt-failed",
            event_type="implementation_failed",
            recorded_on="2026-01-01",
            status_before="attempted",
            status_after="needs_revision",
            attempt_id="TEST-001-A001",
            test_result="failed",
        )
    )
    events.append(
        _event(
            event_id="evt-restart",
            event_type="attempt_started",
            recorded_on="2026-01-02",
            status_before="needs_revision",
            status_after="attempted",
            attempt_id="TEST-001-A002",
        )
    )

    snapshot = replay_events(_parse(events, tmp_path))["TEST-001"]
    assert snapshot.status.value == "attempted"
    assert snapshot.attempt_id == "TEST-001-A002"

    illegal = events + [
        _event(
            event_id="evt-skip",
            event_type="retention_48h_passed",
            recorded_on="2026-01-04",
            status_before="attempted",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            variant_id="rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    with pytest.raises(StateValidationError, match="cannot transition"):
        _parse(illegal, tmp_path)


@pytest.mark.parametrize("level", ["H4", "H5"])
def test_h4_h5_need_h0_fresh_variant_for_retention(
    level: str, tmp_path: Path
) -> None:
    guided = _successful_progression(level=level)

    guided_retention = guided + [
        _event(
            event_id="evt-guided-retention",
            event_type="retention_48h_passed",
            recorded_on="2026-01-03",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            level=level,
            demonstration_only=level == "H5",
            variant_id="rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    with pytest.raises(StateValidationError, match="must use H0"):
        _parse(guided_retention, tmp_path)

    missing_variant = guided + [
        _event(
            event_id="evt-missing-variant",
            event_type="retention_48h_passed",
            recorded_on="2026-01-03",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    with pytest.raises(StateValidationError, match="fresh variant_id"):
        _parse(missing_variant, tmp_path)

    independent = guided + [
        _event(
            event_id="evt-independent-retention",
            event_type="retention_48h_passed",
            recorded_on="2026-01-03",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            variant_id="independent-rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    snapshot = replay_events(_parse(independent, tmp_path))["TEST-001"]
    assert snapshot.status.value == "retained_48h"
    assert not snapshot.requires_independent_variant
    assert not snapshot.demonstration_only


def test_h5_must_be_marked_demonstration_only(tmp_path: Path) -> None:
    event = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after="needs_revision",
        attempt_id="TEST-001-A001",
        level="H5",
        demonstration_only=False,
    )
    with pytest.raises(StateValidationError, match="must be demonstration_only"):
        _parse([event], tmp_path)


def test_assistance_cannot_be_downgraded_within_one_attempt(
    tmp_path: Path,
) -> None:
    events = _successful_progression(level="H4")[:2]
    events.append(
        _event(
            event_id="evt-false-h0",
            event_type="implementation_verified",
            recorded_on="2026-01-01",
            status_before="attempted",
            status_after="implemented",
            attempt_id="TEST-001-A001",
            level="H0",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    )

    with pytest.raises(StateValidationError, match="cannot be downgraded"):
        replay_events(_parse(events, tmp_path))


def test_attempt_lifecycle_cannot_switch_attempt_id(tmp_path: Path) -> None:
    events = _successful_progression()[:2]
    events.append(
        _event(
            event_id="evt-wrong-attempt",
            event_type="implementation_verified",
            recorded_on="2026-01-01",
            status_before="attempted",
            status_after="implemented",
            attempt_id="TEST-001-A999",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    )

    with pytest.raises(StateValidationError, match="preserve the active attempt_id"):
        replay_events(_parse(events, tmp_path))


def test_new_attempt_id_cannot_reuse_prior_attempt(tmp_path: Path) -> None:
    events = _successful_progression()[:2]
    events.extend(
        [
            _event(
                event_id="evt-failed",
                event_type="implementation_failed",
                recorded_on="2026-01-01",
                status_before="attempted",
                status_after="needs_revision",
                attempt_id="TEST-001-A001",
                test_result="failed",
            ),
            _event(
                event_id="evt-reused-attempt",
                event_type="attempt_started",
                recorded_on="2026-01-02",
                status_before="needs_revision",
                status_after="attempted",
                attempt_id="TEST-001-A001",
            ),
        ]
    )

    with pytest.raises(StateValidationError, match="has already been used"):
        replay_events(_parse(events, tmp_path))


def test_retention_requires_exactly_48_elapsed_hours(tmp_path: Path) -> None:
    events = _successful_progression()
    events.append(
        _event(
            event_id="evt-too-early",
            event_type="retention_48h_passed",
            recorded_on="2026-01-02",
            recorded_at="2026-01-02T23:59:59Z",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            variant_id="rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    )
    with pytest.raises(StateValidationError, match="at least 48 elapsed hours"):
        replay_events(_parse(events, tmp_path))


def test_nonlegacy_event_requires_timezone_aware_recorded_at(
    tmp_path: Path,
) -> None:
    event = _successful_progression()[0]
    event["recorded_at"] = "2026-01-01T00:00:00"
    with pytest.raises(StateValidationError, match="timezone-aware RFC3339"):
        _parse([event], tmp_path)

    event["recorded_at"] = None
    with pytest.raises(StateValidationError, match="non-legacy events require"):
        _parse([event], tmp_path)


def test_legacy_import_keeps_date_without_inventing_timestamp(
    tmp_path: Path,
) -> None:
    legacy = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after="needs_revision",
        attempt_id="TEST-001-A001",
    )
    parsed = _parse([legacy], tmp_path)[0]
    assert parsed.recorded_on is not None
    assert parsed.recorded_at is None

    legacy["recorded_at"] = "2026-01-01T00:00:00Z"
    with pytest.raises(StateValidationError, match="recorded_at=null"):
        _parse([legacy], tmp_path)


@pytest.mark.parametrize("status", ["retained_48h", "retained_7d", "mastered"])
def test_legacy_import_cannot_claim_retention_or_mastery(
    status: str,
    tmp_path: Path,
) -> None:
    legacy = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after=status,
        attempt_id="TEST-001-A001",
        level="H5",
        test_result="failed",
    )

    with pytest.raises(
        StateValidationError,
        match="cannot establish retention or mastery",
    ):
        _parse([legacy], tmp_path)


@pytest.mark.parametrize(
    ("status", "test_result", "artifacts", "oral_passed", "message"),
    [
        ("implemented", "failed", ["proof.txt"], None, "passing test evidence"),
        ("implemented", "passed", [], None, "at least one evidence artifact"),
        ("reviewed", "passed", ["proof.txt"], False, "oral_passed=true"),
    ],
)
def test_legacy_implemented_and_reviewed_states_require_evidence(
    status: str,
    test_result: str,
    artifacts: list[str],
    oral_passed: bool | None,
    message: str,
    tmp_path: Path,
) -> None:
    legacy = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after=status,
        attempt_id="TEST-001-A001",
        test_result=test_result,
        artifacts=artifacts,
        oral_passed=oral_passed,
    )

    with pytest.raises(StateValidationError, match=message):
        _parse([legacy], tmp_path)


def test_legacy_review_cannot_seed_a_future_retention_clock(
    tmp_path: Path,
) -> None:
    legacy_review = _event(
        event_id="evt-legacy-review",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after="reviewed",
        attempt_id="TEST-001-A001",
        test_result="passed",
        oral_passed=True,
        artifacts=["proof.txt"],
    )
    retention = _event(
        event_id="evt-retention",
        event_type="retention_48h_passed",
        recorded_on="2026-01-10",
        status_before="reviewed",
        status_after="retained_48h",
        attempt_id="TEST-001-R48",
        variant_id="rewrite-48h",
        test_result="passed",
        artifacts=["proof.txt"],
    )

    with pytest.raises(StateValidationError, match="timestamped review_passed baseline"):
        replay_events(_parse([legacy_review, retention], tmp_path))


def test_note_cannot_switch_the_active_attempt(tmp_path: Path) -> None:
    events = _successful_progression(level="H4")[:2]
    events.append(
        _event(
            event_id="evt-note",
            event_type="note",
            recorded_on="2026-01-02",
            status_before="attempted",
            status_after="attempted",
            attempt_id="TEST-001-A002",
            level="H4",
        )
    )

    with pytest.raises(StateValidationError, match="note cannot change attempt_id"):
        replay_events(_parse(events, tmp_path))


@pytest.mark.parametrize(
    ("level", "demonstration_only", "message"),
    [
        ("H0", False, "assistance level"),
        ("H4", True, "demonstration_only"),
    ],
)
def test_note_cannot_rewrite_assistance_metadata(
    level: str,
    demonstration_only: bool,
    message: str,
    tmp_path: Path,
) -> None:
    events = _successful_progression(level="H4")[:2]
    events.append(
        _event(
            event_id="evt-note",
            event_type="note",
            recorded_on="2026-01-02",
            status_before="attempted",
            status_after="attempted",
            attempt_id="TEST-001-A001",
            level=level,
            demonstration_only=demonstration_only,
        )
    )

    with pytest.raises(StateValidationError, match=message):
        replay_events(_parse(events, tmp_path))


def test_note_preserves_help_metadata_and_independent_variant_debt(
    tmp_path: Path,
) -> None:
    events = _successful_progression(level="H4")
    events.append(
        _event(
            event_id="evt-note",
            event_type="note",
            recorded_on="2026-01-02",
            status_before="reviewed",
            status_after="reviewed",
            attempt_id="TEST-001-A001",
            level="H4",
        )
    )

    snapshot = replay_events(_parse(events, tmp_path))["TEST-001"]

    assert snapshot.latest_event_id == "evt-note"
    assert snapshot.attempt_id == "TEST-001-A001"
    assert snapshot.assistance_level.value == "H4"
    assert not snapshot.demonstration_only
    assert snapshot.requires_independent_variant


def test_rfc3339_offsets_compare_by_actual_elapsed_time(tmp_path: Path) -> None:
    events = _successful_progression()
    events[-1]["recorded_at"] = "2026-01-01T08:00:00+08:00"
    events.append(
        _event(
            event_id="evt-48h",
            event_type="retention_48h_passed",
            recorded_on="2026-01-03",
            recorded_at="2026-01-03T00:00:00Z",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            variant_id="rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    )

    snapshot = replay_events(_parse(events, tmp_path))["TEST-001"]
    assert snapshot.status.value == "retained_48h"


def test_seven_day_and_mastery_gates_use_exact_elapsed_time(
    tmp_path: Path,
) -> None:
    through_48h = _successful_progression() + [
        _event(
            event_id="evt-48h",
            event_type="retention_48h_passed",
            recorded_on="2026-01-03",
            status_before="reviewed",
            status_after="retained_48h",
            attempt_id="TEST-001-R48",
            variant_id="rewrite-48h",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    too_early_7d = through_48h + [
        _event(
            event_id="evt-7d-early",
            event_type="retention_7d_passed",
            recorded_on="2026-01-07",
            recorded_at="2026-01-07T23:59:59Z",
            status_before="retained_48h",
            status_after="retained_7d",
            attempt_id="TEST-001-R7D",
            variant_id="variant-7d",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    with pytest.raises(StateValidationError, match="seven elapsed days"):
        replay_events(_parse(too_early_7d, tmp_path))

    through_7d = through_48h + [
        _event(
            event_id="evt-7d",
            event_type="retention_7d_passed",
            recorded_on="2026-01-08",
            status_before="retained_48h",
            status_after="retained_7d",
            attempt_id="TEST-001-R7D",
            variant_id="variant-7d",
            test_result="passed",
            artifacts=["proof.txt"],
        )
    ]
    too_early_mastery = through_7d + [
        _event(
            event_id="evt-mastery-early",
            event_type="mastery_passed",
            recorded_on="2026-01-21",
            recorded_at="2026-01-21T23:59:59Z",
            status_before="retained_7d",
            status_after="mastered",
            attempt_id="TEST-001-M001",
            variant_id="mixed-21d",
            test_result="passed",
            oral_passed=True,
            artifacts=["proof.txt"],
        )
    ]
    with pytest.raises(StateValidationError, match="21 elapsed days"):
        replay_events(_parse(too_early_mastery, tmp_path))


def test_reused_retention_variant_is_rejected(tmp_path: Path) -> None:
    events = _successful_progression()
    events.extend(
        [
            _event(
                event_id="evt-48h",
                event_type="retention_48h_passed",
                recorded_on="2026-01-03",
                status_before="reviewed",
                status_after="retained_48h",
                attempt_id="TEST-001-R48",
                variant_id="same-variant",
                test_result="passed",
                artifacts=["proof.txt"],
            ),
            _event(
                event_id="evt-7d",
                event_type="retention_7d_passed",
                recorded_on="2026-01-08",
                status_before="retained_48h",
                status_after="retained_7d",
                attempt_id="TEST-001-R7D",
                variant_id="same-variant",
                test_result="passed",
                artifacts=["proof.txt"],
            ),
        ]
    )
    with pytest.raises(StateValidationError, match="is not fresh"):
        replay_events(_parse(events, tmp_path))


def test_current_task_snapshot_must_match_latest_ledger_event(tmp_path: Path) -> None:
    events = _successful_progression()
    parsed = _parse(events, tmp_path)
    snapshots = replay_events(parsed)
    mismatched = parse_current_task_state(
        _state_block(
            status="implemented",
            latest_event_id="evt-reviewed",
            attempt_id="TEST-001-A001",
            assistance_level="H0",
            demonstration_only=False,
        )
    )

    from scripts.state_model import validate_current_task

    with pytest.raises(StateValidationError, match="disagrees with ledger: status"):
        validate_current_task(mismatched, snapshots)


def test_current_task_snapshot_exposes_independent_variant_debt(
    tmp_path: Path,
) -> None:
    events = _successful_progression(level="H4")
    snapshots = replay_events(_parse(events, tmp_path))
    hidden_debt = parse_current_task_state(
        _state_block(
            status="reviewed",
            latest_event_id="evt-reviewed",
            attempt_id="TEST-001-A001",
            assistance_level="H4",
            demonstration_only=False,
            requires_independent_variant=False,
        )
    )

    from scripts.state_model import validate_current_task

    with pytest.raises(
        StateValidationError,
        match="disagrees with ledger: requires_independent_variant",
    ):
        validate_current_task(hidden_debt, snapshots)


def test_current_task_state_requires_explicit_independent_variant_debt() -> None:
    without_debt = _state_block(
        status="needs_revision",
        latest_event_id="evt-legacy",
        attempt_id="TEST-001-A001",
        assistance_level="H1",
        demonstration_only=False,
    ).replace('"requires_independent_variant":false,', "")

    with pytest.raises(
        StateValidationError,
        match="missing keys: requires_independent_variant",
    ):
        parse_current_task_state(without_debt)


def test_repository_current_state_is_consistent() -> None:
    event_count, task_count, snapshot = validate_repository_state(
        repo_root=REPO_ROOT,
        ledger_path=REPO_ROOT / "state" / "TASK_LEDGER.jsonl",
        current_task_path=REPO_ROOT / "state" / "CURRENT_TASK.md",
    )

    assert event_count == 1
    assert task_count == 1
    assert snapshot.task_id == "00A-1"
    assert snapshot.status.value == "needs_revision"
    assert snapshot.assistance_level.value == "H1"
    assert not snapshot.demonstration_only
    assert not snapshot.requires_independent_variant


def test_repository_validation_rejects_missing_evidence_artifact(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    events = [
        _event(
            event_id="evt-legacy",
            event_type="legacy_import",
            recorded_on="2026-01-01",
            status_before=None,
            status_after="needs_revision",
            attempt_id="TEST-001-A001",
            artifacts=["missing.txt"],
            test_result="failed",
        )
    ]
    ledger = state_dir / "TASK_LEDGER.jsonl"
    _write_ledger(ledger, events)
    current = state_dir / "CURRENT_TASK.md"
    current.write_text(
        _state_block(
            status="needs_revision",
            latest_event_id="evt-legacy",
            attempt_id="TEST-001-A001",
            assistance_level="H0",
            demonstration_only=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(StateValidationError, match="does not exist"):
        validate_repository_state(
            repo_root=tmp_path,
            ledger_path=ledger,
            current_task_path=current,
        )


@pytest.mark.parametrize(
    "artifact",
    ["../outside.txt", "/absolute.txt", "C:/secret.txt", r"folder\secret.txt"],
)
def test_evidence_paths_must_be_safe_repository_relative_paths(
    artifact: str, tmp_path: Path
) -> None:
    event = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after="needs_revision",
        attempt_id="TEST-001-A001",
        artifacts=[artifact],
        test_result="failed",
    )
    with pytest.raises(StateValidationError, match="relative path|drive prefix"):
        _parse([event], tmp_path)


def test_unknown_and_duplicate_json_fields_fail_closed(tmp_path: Path) -> None:
    event = _event(
        event_id="evt-legacy",
        event_type="legacy_import",
        recorded_on="2026-01-01",
        status_before=None,
        status_after="needs_revision",
        attempt_id="TEST-001-A001",
    )
    event["unexpected"] = True
    with pytest.raises(StateValidationError, match="unknown keys"):
        _parse([event], tmp_path)

    ledger = tmp_path / "duplicate.jsonl"
    ledger.write_text(
        '{"schema_version":1,"schema_version":1}\n', encoding="utf-8"
    )
    with pytest.raises(StateValidationError, match="duplicate JSON key"):
        load_ledger(ledger)


def test_append_only_validation_accepts_append_and_rejects_rewrite() -> None:
    base = b'{"event_id":"one"}\n'
    validate_append_only(base=base, current=base + b'{"event_id":"two"}\n')

    with pytest.raises(StateValidationError, match="not append-only"):
        validate_append_only(
            base=base,
            current=b'{"event_id":"changed"}\n',
        )


def test_cli_json_is_machine_readable_and_does_not_expose_repo_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["--json"])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["current_task"]["status"] == "needs_revision"
    assert payload["current_task"]["requires_independent_variant"] is False
    assert str(REPO_ROOT) not in output


def test_cli_json_reports_inaccessible_repo_root_without_path_or_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_root = tmp_path / "private-user-name" / "missing-repository"

    exit_code = main(["--json", "--repo-root", str(missing_root)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["error"] == "repository root is not accessible"
    assert str(tmp_path) not in captured.out
    assert "Traceback" not in captured.out
    assert captured.err == ""
