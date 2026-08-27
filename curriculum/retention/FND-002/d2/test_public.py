import pytest


def test_normalizes_changed_field_names_and_copies_list(submission):
    record = {"id": "x", "target": 2, "outputs": [2, 1]}
    result = submission.normalize_inference_record(record)
    assert result == {"sample_id": "x", "label": 2, "predictions": [2, 1]}
    assert result["predictions"] is not record["outputs"]


def test_requires_exact_fields(submission):
    with pytest.raises(ValueError):
        submission.normalize_inference_record({"id": "x", "target": 1, "outputs": [1], "extra": 0})


def test_rejects_bool_as_integer(submission):
    with pytest.raises(ValueError):
        submission.normalize_inference_record({"id": "x", "target": True, "outputs": [1]})


def test_rejects_empty_outputs(submission):
    with pytest.raises(ValueError):
        submission.normalize_inference_record({"id": "x", "target": 1, "outputs": []})


def test_does_not_mutate_input(submission):
    record = {"id": "x", "target": 1, "outputs": [1, 0]}
    before = {"id": "x", "target": 1, "outputs": [1, 0]}
    submission.normalize_inference_record(record)
    assert record == before
