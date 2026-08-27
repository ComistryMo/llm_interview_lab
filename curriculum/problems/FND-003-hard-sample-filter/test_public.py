import copy
import pytest

def sample(sid, label, predictions):
    return {"sample_id": sid, "label": label, "predictions": predictions}

def test_filters_by_error_count_and_preserves_order(submission):
    items = [sample("a", 1, [1, 1]), sample("b", 1, [0, 1]), sample("c", 2, [0, 1])]
    assert [item["sample_id"] for item in submission.mine_hard_samples(items, 1)] == ["b", "c"]

def test_threshold_changes_selection(submission):
    items = [sample("a", 0, [1, 0]), sample("b", 0, [1, 2])]
    assert [x["sample_id"] for x in submission.mine_hard_samples(items, 2)] == ["b"]

def test_empty_input_returns_empty_list(submission):
    assert submission.mine_hard_samples([], 1) == []

@pytest.mark.parametrize("items,threshold", [({}, 1), ([], 0), ([], True), ([{"sample_id":"x","label":0,"predictions":[]}], 1)])
def test_invalid_contract_raises(submission, items, threshold):
    with pytest.raises(ValueError):
        submission.mine_hard_samples(items, threshold)

def test_input_is_not_mutated_and_result_does_not_alias(submission):
    items = [sample("a", 0, [1])]
    before = copy.deepcopy(items)
    result = submission.mine_hard_samples(items)
    result[0]["predictions"].append(2)
    assert items == before

