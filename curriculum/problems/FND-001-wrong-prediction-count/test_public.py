"""Public contract tests for FND-001.

The ``submission`` fixture is injected by the repository grader. This file is
deliberately unaware of source templates and learner storage paths.
"""

from __future__ import annotations

import pytest


def test_counts_mixed_predictions(submission) -> None:
    assert submission.count_wrong_predictions(2, [2, 1, 2, 3, 2]) == 2


def test_counts_all_correct_and_all_wrong(submission) -> None:
    assert submission.count_wrong_predictions(4, [4, 4, 4]) == 0
    assert submission.count_wrong_predictions(4, [1, 2, 3]) == 3


@pytest.mark.parametrize("label", [True, False, 1.0, "1", None])
def test_rejects_non_strict_integer_label(submission, label) -> None:
    with pytest.raises(ValueError):
        submission.count_wrong_predictions(label, [1])


class CustomList(list):
    """A list subclass is outside this task's strict built-in-list contract."""


@pytest.mark.parametrize("predictions", [(1,), None, CustomList([1])])
def test_rejects_non_strict_list_container(submission, predictions) -> None:
    with pytest.raises(ValueError):
        submission.count_wrong_predictions(1, predictions)


@pytest.mark.parametrize("invalid", [True, False, 1.0, "1", None])
def test_rejects_non_strict_integer_prediction(submission, invalid) -> None:
    predictions = [1, invalid, 2]
    snapshot = list(predictions)
    with pytest.raises(ValueError):
        submission.count_wrong_predictions(1, predictions)
    assert predictions == snapshot


def test_rejects_empty_predictions(submission) -> None:
    with pytest.raises(ValueError):
        submission.count_wrong_predictions(1, [])


def test_does_not_modify_valid_input(submission) -> None:
    predictions = [1, 2, 1]
    snapshot = list(predictions)
    result = submission.count_wrong_predictions(1, predictions)
    assert predictions == snapshot
    assert type(result) is int
