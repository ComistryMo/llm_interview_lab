import pytest


def test_merges_overlapping_labels(submission):
    assert submission.merge_error_summaries([{1: (2, 3)}, {0: (1, 1), 1: (4, 2)}]) == {
        1: (6, 5), 0: (1, 1)
    }


def test_empty_input_and_empty_parts(submission):
    assert submission.merge_error_summaries([]) == {}
    assert submission.merge_error_summaries([{}, {}]) == {}


def test_rejects_bool_label(submission):
    with pytest.raises(ValueError):
        submission.merge_error_summaries([{True: (1, 0)}])


def test_rejects_negative_or_malformed_counts(submission):
    for value in [(-1, 0), (1,), [1, 0]]:
        with pytest.raises(ValueError):
            submission.merge_error_summaries([{1: value}])


def test_does_not_mutate_parts(submission):
    parts = [{1: (2, 1)}]
    submission.merge_error_summaries(parts)
    assert parts == [{1: (2, 1)}]
