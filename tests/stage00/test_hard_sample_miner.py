import copy

import pytest

from src.stage00.hard_sample_miner import (
    count_wrong_predictions,
    select_hard_samples,
    summarize_hard_samples,
)


pytestmark = [pytest.mark.training, pytest.mark.locked]


def make_samples():
    return [
        {"id": "a", "label": 1, "predictions": [1, 0, 0]},  # 2 wrong
        {"id": "b", "label": 0, "predictions": [0, 0, 1]},  # 1 wrong
        {"id": "c", "label": 0, "predictions": [1, 1, 0]},  # 2 wrong
        {"id": "d", "label": 1, "predictions": [0, 0, 0]},  # 3 wrong
    ]


def test_count_wrong_predictions():
    assert count_wrong_predictions(1, [1, 0, 0]) == 2
    assert count_wrong_predictions(0, [0, 0, 0]) == 0


def test_count_wrong_predictions_rejects_empty_input():
    with pytest.raises(ValueError):
        count_wrong_predictions(1, [])


def test_select_hard_samples_keeps_order():
    result = select_hard_samples(make_samples(), min_wrong=2)
    assert [sample["id"] for sample in result] == ["a", "c", "d"]


def test_select_hard_samples_does_not_mutate_input():
    samples = make_samples()
    original = copy.deepcopy(samples)
    select_hard_samples(samples, min_wrong=2)
    assert samples == original


def test_select_hard_samples_rejects_invalid_threshold():
    with pytest.raises(ValueError):
        select_hard_samples(make_samples(), min_wrong=0)


def test_select_hard_samples_rejects_missing_fields():
    with pytest.raises(ValueError):
        select_hard_samples([{"id": "broken", "label": 1}], min_wrong=2)


def test_summarize_hard_samples():
    result = summarize_hard_samples(make_samples(), min_wrong=2)
    assert result["total"] == 4
    assert result["hard_count"] == 3
    assert result["hard_ratio"] == pytest.approx(0.75)
    assert result["hard_count_by_label"] == {0: 1, 1: 2}


def test_summarize_empty_samples():
    result = summarize_hard_samples([], min_wrong=2)
    assert result == {
        "total": 0,
        "hard_count": 0,
        "hard_ratio": 0.0,
        "hard_count_by_label": {},
    }
