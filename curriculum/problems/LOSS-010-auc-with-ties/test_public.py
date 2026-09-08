import math
import pytest

np = pytest.importorskip("numpy")


@pytest.mark.parametrize("scores,want", [([0, 1], 1), ([1, 0], 0), ([0.5, 0.5], 0.5)])
def test_pair_order(submission, scores, want):
    assert submission.binary_auc([0, 1], scores) == want


def test_group_ties(submission):
    assert submission.binary_auc([0, 1, 1, 0], [1, 1, 2, 0]) == pytest.approx(0.875)


def test_permutation(submission):
    assert submission.binary_auc([1, 0, 0, 1], [1, 1, 0, 2]) == pytest.approx(0.875)


def test_single_class_rejected(submission):
    with pytest.raises(ValueError):
        submission.binary_auc([1, 1], [0, 1])


def test_input_preserved(submission):
    y = np.array([0, 1])
    s = np.array([1.0, 0.0])
    submission.binary_auc(y, s)
    np.testing.assert_array_equal(s, [1, 0])
