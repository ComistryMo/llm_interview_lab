import copy
import pytest


def item(sid, category, label, predictions):
    return {"sample_id": sid, "category": category, "label": label, "predictions": predictions}


def test_counts_hard_samples_by_category(submission):
    samples = [item("a", "ocr", 0, [1]), item("b", "ocr", 0, [0]), item("c", "chart", 1, [0, 2])]
    assert submission.hard_sample_counts(samples, 1) == {"ocr": 1, "chart": 1}


def test_threshold_and_empty(submission):
    assert submission.hard_sample_counts([item("a", "x", 0, [1, 0])], 2) == {}
    assert submission.hard_sample_counts([], 1) == {}


def test_input_is_not_mutated(submission):
    samples = [item("a", "x", 0, [1])]
    before = copy.deepcopy(samples)
    submission.hard_sample_counts(samples)
    assert samples == before


@pytest.mark.parametrize("samples", [[item("a", "", 0, [1])], [item("a", 2, 0, [1])], [item("a", "x", False, [1])]])
def test_invalid_records(submission, samples):
    with pytest.raises(ValueError):
        submission.hard_sample_counts(samples)


def test_returns_fresh_mapping(submission):
    samples = [item("a", "x", 0, [1])]
    first = submission.hard_sample_counts(samples)
    second = submission.hard_sample_counts(samples)
    assert first == second and first is not second
