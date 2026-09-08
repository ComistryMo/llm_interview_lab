import math
import pytest

np = pytest.importorskip("numpy")


def test_nearest(submission):
    assert submission.knn_predict([[0], [2]], [3, 4], [[2]]).tolist() == [4]


def test_equal_distance_original_order(submission):
    assert submission.knn_predict([[0], [2]], [4, 3], [[1]]).tolist() == [4]


def test_vote_tie_smaller_class(submission):
    assert submission.knn_predict([[0], [2]], [4, 3], [[1]], 2).tolist() == [3]


def test_cosine_differs_from_euclidean(submission):
    assert submission.knn_predict(
        [[100, 0], [1, 1]], [7, 8], [[1, 0]], metric="cosine"
    ).tolist() == [7]


def test_cosine_zero_rejected(submission):
    with pytest.raises(ValueError):
        submission.knn_predict([[0, 0]], [0], [[1, 0]], metric="cosine")


def test_empty_queries(submission):
    assert submission.knn_predict([[1, 1]], [0], np.empty((0, 2))).size == 0
