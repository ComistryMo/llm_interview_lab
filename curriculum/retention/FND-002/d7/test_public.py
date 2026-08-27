import pytest


def test_partitions_valid_and_invalid_records(submission):
    samples = [
        {"sample_id": "a", "label": 1, "predictions": [1, 0]},
        {"sample_id": "", "label": 1, "predictions": [1]},
        {"sample_id": "b", "label": 0, "predictions": [0]},
    ]
    valid, rejected = submission.partition_valid_samples(samples)
    assert valid == [samples[0], samples[2]]
    assert rejected == [1]


def test_returns_defensive_nested_copies(submission):
    source = [{"sample_id": "a", "label": 1, "predictions": [1]}]
    valid, _ = submission.partition_valid_samples(source)
    assert valid[0] is not source[0]
    assert valid[0]["predictions"] is not source[0]["predictions"]


def test_rejects_non_list_container(submission):
    with pytest.raises(ValueError):
        submission.partition_valid_samples(())


def test_rejects_bool_prediction_without_aborting_batch(submission):
    valid, rejected = submission.partition_valid_samples([
        {"sample_id": "bad", "label": 1, "predictions": [True]},
    ])
    assert valid == [] and rejected == [0]


def test_empty_batch(submission):
    assert submission.partition_valid_samples([]) == ([], [])
