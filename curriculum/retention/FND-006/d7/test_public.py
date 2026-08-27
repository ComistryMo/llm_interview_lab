import pytest


def test_pads_last_batch_and_emits_mask(submission):
    assert list(submission.iter_padded_batches([1, 2, 3], 2, 0)) == [([1, 2], [True, True]), ([3, 0], [True, False])]


def test_full_batches_have_all_true_mask(submission):
    assert list(submission.iter_padded_batches([1, 2], 2, "x")) == [([1, 2], [True, True])]


def test_empty_input_is_empty(submission):
    assert list(submission.iter_padded_batches([], 3)) == []


def test_rejects_invalid_arguments(submission):
    for items, size in [((1,), 1), ([1], 0), ([1], True)]:
        with pytest.raises(ValueError):
            list(submission.iter_padded_batches(items, size))


def test_output_lists_are_independent(submission):
    items = [1, 2, 3]
    output = list(submission.iter_padded_batches(items, 2, 0))
    output[-1][0][0] = 99
    output[-1][1][0] = False
    assert items == [1, 2, 3]
