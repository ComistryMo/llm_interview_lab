import pytest


def test_yields_offsets_and_batches(submission):
    assert list(submission.iter_indexed_batches(["a", "b", "c"], 2)) == [(0, ["a", "b"]), (2, ["c"])]


def test_is_iterator_and_empty_is_empty(submission):
    iterator = submission.iter_indexed_batches([], 2)
    assert iter(iterator) is iterator and list(iterator) == []


def test_rejects_invalid_batch_size(submission):
    for value in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            list(submission.iter_indexed_batches([1], value))


def test_rejects_non_list_items(submission):
    with pytest.raises(ValueError):
        list(submission.iter_indexed_batches((1, 2), 1))


def test_batches_do_not_alias_input_container(submission):
    items = [{"x": 1}, {"x": 2}]
    batches = list(submission.iter_indexed_batches(items, 1))
    batches[0][1].append({"x": 3})
    assert items == [{"x": 1}, {"x": 2}]
