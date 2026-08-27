import copy
import pytest


def test_collects_wrong_indices_in_order(submission):
    records = [{"label": 1, "prediction": 0}, {"label": 2, "prediction": 2}, {"label": -1, "prediction": 1}]
    assert submission.wrong_record_indices(records) == [0, 2]


def test_empty_records(submission):
    assert submission.wrong_record_indices([]) == []


def test_input_is_not_mutated(submission):
    records = [{"label": 0, "prediction": 1}]
    before = copy.deepcopy(records)
    submission.wrong_record_indices(records)
    assert records == before


@pytest.mark.parametrize("records", [({},), [{"label": 1}], [{"label": True, "prediction": 1}], [{"label": 1, "prediction": 1.0}]])
def test_invalid_record_contract(submission, records):
    with pytest.raises(ValueError):
        submission.wrong_record_indices(records)


def test_extra_fields_are_ignored(submission):
    assert submission.wrong_record_indices([{"label": 0, "prediction": 1, "id": "x"}]) == [0]
