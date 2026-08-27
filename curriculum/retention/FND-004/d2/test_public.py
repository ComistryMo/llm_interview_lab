import pytest


def test_groups_sample_and_error_counts(submission):
    samples = [
        {"sample_id": "a", "label": 1, "predictions": [1, 0, 2]},
        {"sample_id": "b", "label": 1, "predictions": [1]},
        {"sample_id": "c", "label": 0, "predictions": [1, 0]},
    ]
    assert submission.summarize_errors_by_label(samples) == {1: (2, 2), 0: (1, 1)}


def test_empty_input(submission):
    assert submission.summarize_errors_by_label([]) == {}


def test_rejects_invalid_nested_contract(submission):
    with pytest.raises(ValueError):
        submission.summarize_errors_by_label([{"sample_id": "a", "label": True, "predictions": [1]}])


def test_rejects_non_list_outer_container(submission):
    with pytest.raises(ValueError):
        submission.summarize_errors_by_label(())


def test_does_not_mutate_records(submission):
    samples = [{"sample_id": "a", "label": 1, "predictions": [0]}]
    submission.summarize_errors_by_label(samples)
    assert samples == [{"sample_id": "a", "label": 1, "predictions": [0]}]
