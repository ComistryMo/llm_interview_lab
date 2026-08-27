import pytest

def test_valid_sample_is_copied(submission):
    source = {"sample_id": "s-1", "label": 2, "predictions": [2, 1]}
    result = submission.validate_sample(source)
    assert result == source
    assert result is not source and result["predictions"] is not source["predictions"]

def test_input_is_not_mutated_or_aliased(submission):
    source = {"sample_id": "s", "label": 0, "predictions": [0]}
    result = submission.validate_sample(source)
    result["predictions"].append(1)
    assert source == {"sample_id": "s", "label": 0, "predictions": [0]}

@pytest.mark.parametrize("sample", [[], {"sample_id": "s", "label": 0}, {"sample_id": "", "label": 0, "predictions": [0]}])
def test_invalid_container_or_fields_raise(submission, sample):
    with pytest.raises(ValueError):
        submission.validate_sample(sample)

@pytest.mark.parametrize("field,value", [("label", True), ("label", 1.0), ("predictions", [0, False]), ("predictions", [])])
def test_strict_types_and_nonempty_predictions(submission, field, value):
    sample = {"sample_id": "s", "label": 0, "predictions": [0]}
    sample[field] = value
    with pytest.raises(ValueError):
        submission.validate_sample(sample)

def test_extra_fields_are_preserved_in_new_mapping(submission):
    source = {"sample_id": "s", "label": 1, "predictions": [1], "source": "toy"}
    assert submission.validate_sample(source)["source"] == "toy"

