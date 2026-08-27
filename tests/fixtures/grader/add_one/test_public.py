"""Infrastructure-only public tests for the grader protocol."""

from __future__ import annotations


def test_adds_one_to_positive_value(submission) -> None:
    assert submission.add_one(4) == 5


def test_adds_one_to_negative_value(submission) -> None:
    assert submission.add_one(-2) == -1
