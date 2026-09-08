import math
import pytest

np = pytest.importorskip("numpy")


def test_closed_form(submission):
    labels, costs, inertia = submission.kmeans(
        np.array([[0.0], [2.0], [10.0], [12.0]]), np.array([[0.0], [10.0]])
    )
    np.testing.assert_allclose(costs[:, 0], [1, 11])
    assert inertia == pytest.approx(4)
    assert labels.tolist() == [0, 0, 1, 1]


def test_empty_cluster_preserves_center(submission):
    _, c, _ = submission.kmeans(np.zeros((3, 1)), np.array([[0.0], [8.0]]))
    np.testing.assert_allclose(c[:, 0], [0, 8])


def test_one_iteration_returns_consistent_labels(submission):
    x = np.array([[0.0], [4.0], [6.0]])
    labels, c, loss = submission.kmeans(x, np.array([[0.0], [10.0]]), max_iter=1)
    d = ((x[:, None] - c) ** 2).sum(2)
    np.testing.assert_array_equal(labels, d.argmin(1))
    assert loss == pytest.approx(d[np.arange(3), labels].sum())


def test_inputs_unchanged(submission):
    x = np.array([[0.0], [2.0]])
    c = x.copy()
    submission.kmeans(x, c)
    np.testing.assert_array_equal(c, x)


def test_invalid_cluster_count(submission):
    with pytest.raises(ValueError):
        submission.kmeans(np.ones((1, 2)), np.ones((2, 2)))
