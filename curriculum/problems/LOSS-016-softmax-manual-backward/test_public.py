import math
import pytest

np = pytest.importorskip("numpy")


def test_large_equal_logits(submission):
    p, g = submission.softmax_backward(
        np.array([[1000.0, 1000.0]]), np.array([[1.0, 0.0]])
    )
    np.testing.assert_allclose(p, [[0.5, 0.5]])
    np.testing.assert_allclose(g, [[0.25, -0.25]])


def test_uniform_upstream(submission):
    _, g = submission.softmax_backward(np.array([[1.0, 2.0, 3.0]]), np.ones((1, 3)))
    np.testing.assert_allclose(g, 0, atol=1e-15)


def test_gradient_row_sum(submission):
    p, g = submission.softmax_backward(
        np.arange(6.0).reshape(2, 3), np.arange(6.0).reshape(2, 3)
    )
    np.testing.assert_allclose(p.sum(1), 1)
    np.testing.assert_allclose(g.sum(1), 0, atol=1e-15)


def test_shift_invariant(submission):
    x = np.array([[1.0, 2.0]])
    g = np.array([[3.0, 5.0]])
    a = submission.softmax_backward(x, g)
    b = submission.softmax_backward(x + 20, g)
    np.testing.assert_allclose(a, b)


def test_shape_error(submission):
    with pytest.raises(ValueError):
        submission.softmax_backward(np.ones((2, 3)), np.ones((3, 2)))
