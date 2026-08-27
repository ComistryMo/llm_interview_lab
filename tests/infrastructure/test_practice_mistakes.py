from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from llm_interview_lab.events import summarize_mistakes


pytestmark = pytest.mark.infrastructure


def _event(
    sequence: int,
    event_type: str,
    *,
    problem_id: str | None = "FND-001",
    attempt_id: str | None = "attempt-0001",
    timestamp: str = "2026-01-01T00:00:00+00:00",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "event_id": f"evt-{sequence:04d}",
        "timestamp": timestamp,
        "profile_id": "synthetic-learner",
        "event_type": event_type,
        "problem_id": problem_id,
        "attempt_id": attempt_id,
        "payload": payload or {},
    }


def _started(sequence: int, problem_id: str = "FND-001") -> dict[str, Any]:
    return _event(
        sequence,
        "task_started",
        problem_id=problem_id,
        payload={
            "submission_relpath": (
                f"workspace/profiles/synthetic-learner/submissions/{problem_id}/attempt-0001/submission.py"
            )
        },
    )


def _public_test(sequence: int, status: str, *, problem_id: str = "FND-001", timestamp: str) -> dict[str, Any]:
    passed = 5 if status == "passed" else 0
    failed = 0 if status == "passed" else 1
    return _event(
        sequence,
        "public_tests_run",
        problem_id=problem_id,
        timestamp=timestamp,
        payload={
            "submission_sha256": str(sequence % 10) * 64,
            "exit_code": 0 if status == "passed" else 1,
            "status": status,
            "passed": passed,
            "failed": failed,
            "duration_ms": sequence,
        },
    )


def _review(sequence: int, contract: str, oral: str, *, problem_id: str = "FND-001", timestamp: str) -> dict[str, Any]:
    return _event(
        sequence,
        "review_completed",
        problem_id=problem_id,
        timestamp=timestamp,
        payload={
            "contract_status": contract,
            "oral_status": oral,
            "code_explanation": "synthetic explanation",
            "complexity": "O(n)",
            "boundary_conditions": "synthetic boundary evidence",
        },
    )


def test_summary_preserves_physical_failure_history_after_matching_recovery() -> None:
    events = [
        _started(1),
        _public_test(2, "failed", timestamp="2030-01-01T00:00:00+00:00"),
        _public_test(3, "timed_out", timestamp="2040-01-01T00:00:00+00:00"),
        _public_test(4, "passed", timestamp="2020-01-01T00:00:00+00:00"),
        _review(5, "passed", "failed", timestamp="2035-01-01T00:00:00+00:00"),
        _review(6, "passed", "passed", timestamp="2019-01-01T00:00:00+00:00"),
        _event(7, "task_failed", timestamp="2010-01-01T00:00:00+00:00"),
        _event(8, "task_implemented", payload={"submission_sha256": "8" * 64}),
    ]

    (summary,) = summarize_mistakes(events)

    assert summary.problem_id == "FND-001"
    assert summary.failure_count == 4
    assert summary.last_failed_at == datetime(2010, 1, 1, tzinfo=timezone.utc)
    assert summary.last_failed_sequence == 6
    assert summary.last_failure_kind == "task_failed"
    assert summary.current_evidence_recovered
    assert [item.failure_kind for item in summary.failure_history] == [
        "public_tests_failed",
        "public_tests_timed_out",
        "review_oral_failed",
        "task_failed",
    ]
    assert all(item.recovered for item in summary.failure_history)


def test_summary_keeps_unrecovered_review_separate_from_recovered_test_evidence() -> None:
    events = [
        _started(1, "FND-001"),
        _public_test(2, "failed", problem_id="FND-001", timestamp="2026-01-02T00:00:00+00:00"),
        _public_test(3, "passed", problem_id="FND-001", timestamp="2026-01-03T00:00:00+00:00"),
        _started(4, "FND-002"),
        _review(5, "failed", "failed", problem_id="FND-002", timestamp="2026-01-04T00:00:00+00:00"),
        _public_test(6, "passed", problem_id="FND-002", timestamp="2026-01-05T00:00:00+00:00"),
    ]

    first, second = summarize_mistakes(events)

    assert first.problem_id == "FND-001"
    assert first.current_evidence_recovered
    assert second.problem_id == "FND-002"
    assert second.failure_count == 1
    assert second.last_failure_kind == "review_contract_and_oral_failed"
    assert not second.current_evidence_recovered
    assert not second.failure_history[0].recovered


def test_mastery_recovers_evidence_without_erasing_the_failure() -> None:
    events = [
        _started(1),
        _event(2, "task_failed", timestamp="2026-01-02T00:00:00+00:00"),
        _event(3, "task_mastered", payload={"submission_sha256": "3" * 64}),
    ]

    (summary,) = summarize_mistakes(events)

    assert summary.failure_count == 1
    assert summary.current_evidence_recovered
    assert summary.failure_history[0].recovered


def test_success_only_history_has_no_mistake_summary() -> None:
    events = [
        _started(1),
        _public_test(2, "passed", timestamp="2026-01-02T00:00:00+00:00"),
        _review(3, "passed", "passed", timestamp="2026-01-03T00:00:00+00:00"),
    ]

    assert summarize_mistakes(event for event in events) == ()


def test_infrastructure_test_failures_do_not_enter_the_learner_mistake_view() -> None:
    events = [
        _started(1),
        _public_test(
            2,
            "collection_error",
            timestamp="2026-01-02T00:00:00+00:00",
        ),
        _public_test(
            3,
            "internal_error",
            timestamp="2026-01-03T00:00:00+00:00",
        ),
    ]

    assert summarize_mistakes(events) == ()
