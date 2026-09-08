import math
import pytest

np = pytest.importorskip("numpy")


def test_overlapping(submission):
    assert submission.nms(
        np.array([[0, 0, 2, 2], [0, 0, 2, 2], [4, 4, 5, 5]]), [0.8, 0.9, 0.7]
    ).tolist() == [1, 2]


def test_ties(submission):
    assert submission.nms(np.array([[0, 0, 2, 2]] * 2), [1, 1]).tolist() == [0]


def test_equal_threshold(submission):
    assert submission.nms(np.array([[0, 0, 2, 2]] * 2), [1, 1], 1).tolist() == [0, 1]


def test_empty(submission):
    assert submission.nms(np.empty((0, 4)), []).shape == (0,)


def test_degenerate(submission):
    assert submission.nms(np.zeros((2, 4)), [1, 1]).tolist() == [0, 1]


def test_invalid_box(submission):
    with pytest.raises(ValueError):
        submission.nms([[1, 0, 0, 2]], [1])
