import copy

import pytest

from src.stage00.hard_sample_miner import count_wrong_predictions


pytestmark = [pytest.mark.training, pytest.mark.current]


def test_counts_mixed_predictions() -> None:
    assert count_wrong_predictions(1, [1, 0, 0]) == 2


def test_counts_all_correct() -> None:
    assert count_wrong_predictions(0, [0, 0, 0]) == 0


def test_counts_all_wrong() -> None:
    assert count_wrong_predictions(1, [0, 0, 0]) == 3


def test_rejects_empty_predictions() -> None:
    with pytest.raises(ValueError):
        count_wrong_predictions(1, [])


def test_rejects_non_integer_prediction() -> None:
    with pytest.raises(ValueError):
        count_wrong_predictions(1, [1, "0", 0])  # type: ignore[list-item]


def test_does_not_mutate_input() -> None:
    predictions = [1, 0, 0]
    original = copy.deepcopy(predictions)
    count_wrong_predictions(1, predictions)
    assert predictions == original
