import copy
import math
import pytest

def test_summary_counts_and_rate(submission):
    samples = [{"sample_id":"a","label":1,"predictions":[1,0]}, {"sample_id":"b","label":0,"predictions":[1,2,0]}]
    result = submission.summarize_hard_samples(samples)
    assert result == {"total_samples":2, "total_predictions":5, "total_errors":3, "hard_samples":2, "error_rate":0.6}

def test_empty_input_has_well_defined_zeros(submission):
    assert submission.summarize_hard_samples([]) == {"total_samples":0, "total_predictions":0, "total_errors":0, "hard_samples":0, "error_rate":0.0}

def test_all_correct_is_not_hard(submission):
    result = submission.summarize_hard_samples([{"sample_id":"x","label":3,"predictions":[3,3]}])
    assert result["hard_samples"] == 0 and math.isclose(result["error_rate"], 0.0)

@pytest.mark.parametrize("bad", [None, {}, [{"sample_id":"x","label":True,"predictions":[1]}], [{"sample_id":"x","label":1,"predictions":[]}]] )
def test_invalid_samples_raise_value_error(submission, bad):
    with pytest.raises(ValueError):
        submission.summarize_hard_samples(bad)

def test_summary_does_not_mutate_input(submission):
    samples = [{"sample_id":"x","label":0,"predictions":[1,0]}]
    before = copy.deepcopy(samples)
    submission.summarize_hard_samples(samples)
    assert samples == before

