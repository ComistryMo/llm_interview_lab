import copy
import pytest


def item(sid, label, predictions):
    return {"sample_id": sid, "label": label, "predictions": predictions}


def test_ids_preserve_order(submission):
    samples = [item("a", 0, [0]), item("b", 0, [1, 0]), item("c", 1, [0, 2])]
    assert submission.hard_sample_ids(samples, 1) == ["b", "c"]


def test_threshold_and_empty_input(submission):
    assert submission.hard_sample_ids([item("a", 0, [1, 2])], 2) == ["a"]
    assert submission.hard_sample_ids([], 1) == []


def test_input_is_not_mutated(submission):
    samples = [item("a", 0, [1])]
    before = copy.deepcopy(samples)
    submission.hard_sample_ids(samples)
    assert samples == before


@pytest.mark.parametrize("samples,threshold", [({}, 1), ([], 0), ([item(1, 0, [1])], 1), ([item("x", True, [1])], 1)])
def test_invalid_contract(submission, samples, threshold):
    with pytest.raises(ValueError):
        submission.hard_sample_ids(samples, threshold)


def test_prediction_bool_is_rejected(submission):
    with pytest.raises(ValueError):
        submission.hard_sample_ids([item("x", 1, [True])])
