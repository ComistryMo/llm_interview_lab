import math
import pytest

np = pytest.importorskip("numpy")


def test_zero_logits(submission):
    r = submission.logistic_step(np.ones((2, 1)), np.array([0, 1]), np.zeros(1), 0.0)
    assert r[0] == pytest.approx(math.log(2))
    np.testing.assert_allclose(r[1], 0)


@pytest.mark.parametrize(
    "z,y,want", [(1000.0, 1, 0), (1000.0, 0, 1000), (-1000.0, 0, 0), (-1000.0, 1, 1000)]
)
def test_extremes(submission, z, y, want):
    assert submission.logistic_step(np.ones((1, 1)), np.array([y]), np.array([z]), 0.0)[
        0
    ] == pytest.approx(want)


def test_bias_not_regularized(submission):
    r = submission.logistic_step(
        np.zeros((1, 1)), np.array([1]), np.array([2.0]), 0.0, l2=0.5
    )
    assert r[0] == pytest.approx(math.log(2) + 1)
    np.testing.assert_allclose(r[1], [1])
    assert r[2] == -0.5


def test_sgd_update(submission):
    r = submission.logistic_step(
        np.ones((1, 1)), np.array([1]), np.zeros(1), 0.0, lr=0.2
    )
    np.testing.assert_allclose(r[3], [0.1])
    assert r[4] == pytest.approx(0.1)


def test_invalid_regularizer(submission):
    with pytest.raises(ValueError):
        submission.logistic_step(
            np.ones((1, 1)), np.array([1]), np.zeros(1), 0.0, l2=-1
        )
