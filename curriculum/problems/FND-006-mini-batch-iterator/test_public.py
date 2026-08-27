import pytest

def test_even_batches_preserve_order(submission):
    assert list(submission.iter_minibatches([0,1,2,3], 2)) == [[0,1],[2,3]]

def test_short_last_batch_is_kept_by_default(submission):
    assert list(submission.iter_minibatches([0,1,2], 2)) == [[0,1],[2]]

def test_drop_last_removes_only_incomplete_batch(submission):
    assert list(submission.iter_minibatches([0,1,2], 2, True)) == [[0,1]]
    assert list(submission.iter_minibatches([0,1,2,3], 2, True)) == [[0,1],[2,3]]

def test_empty_input_and_iterator_contract(submission):
    batches = submission.iter_minibatches([], 3)
    assert iter(batches) is batches
    assert list(batches) == []

@pytest.mark.parametrize("items,size,drop", [((),2,False), ([],0,False), ([],True,False), ([],2,1)])
def test_invalid_arguments_raise_value_error(submission, items, size, drop):
    with pytest.raises(ValueError):
        list(submission.iter_minibatches(items, size, drop))

def test_batches_are_new_lists_and_input_is_unchanged(submission):
    items = [1,2]
    batch = next(submission.iter_minibatches(items, 2))
    batch.append(3)
    assert items == [1,2]

