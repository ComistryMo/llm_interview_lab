import math
import pytest

np = pytest.importorskip("numpy")


def test_endpoints(submission):
    q, s, r = submission.quantize_per_channel(np.array([[-127.0, 0, 127.0]]))
    np.testing.assert_array_equal(q, [[-127, 0, 127]])
    assert q.dtype == np.int8
    np.testing.assert_allclose(s, [[1]])


def test_zero_row(submission):
    q, s, r = submission.quantize_per_channel(np.zeros((1, 4)))
    np.testing.assert_array_equal(q, 0)
    np.testing.assert_array_equal(s, 1)


def test_independent_scales(submission):
    q, s, r = submission.quantize_per_channel(np.array([[1.0, 3.0], [100, 300]]))
    assert s.shape == (2, 1)
    assert s[1, 0] / s[0, 0] == pytest.approx(100)
    np.testing.assert_array_equal(q[0], q[1])


def test_ties_even(submission):
    q, _, _ = submission.quantize_per_channel(np.array([[127.0, 0.5, 1.5, 2.5, -1.5]]))
    np.testing.assert_array_equal(q, [[127, 0, 2, 2, -2]])


def test_error_bound(submission):
    w = np.random.default_rng(2).normal(size=(4, 8))
    q, s, r = submission.quantize_per_channel(w)
    assert np.all(np.abs(r - w) <= s / 2 + 1e-12)
