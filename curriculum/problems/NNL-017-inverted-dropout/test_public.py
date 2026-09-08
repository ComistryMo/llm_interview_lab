import math
import pytest

np = pytest.importorskip("numpy")


def test_zero_probability(submission):
    x = np.arange(6.0)
    y, m = submission.dropout_forward(x, 0)
    np.testing.assert_array_equal(y, x)
    np.testing.assert_array_equal(m, 1)


def test_eval_identity(submission):
    x = np.arange(6.0)
    y, m = submission.dropout_forward(x, 0.7, False)
    np.testing.assert_array_equal(y, x)


def test_seed_reproducible(submission):
    x = np.ones(100)
    a = submission.dropout_forward(x, 0.5, rng=np.random.default_rng(9))
    b = submission.dropout_forward(x, 0.5, rng=np.random.default_rng(9))
    np.testing.assert_array_equal(a, b)


def test_backward_same_mask(submission):
    y, m = submission.dropout_forward(np.ones(20), 0.5, rng=np.random.default_rng(2))
    np.testing.assert_array_equal(
        submission.dropout_backward(np.ones(20) * 3, m), y * 3
    )


def test_invalid_probability(submission):
    with pytest.raises(ValueError):
        submission.dropout_forward(np.ones(2), 1)
