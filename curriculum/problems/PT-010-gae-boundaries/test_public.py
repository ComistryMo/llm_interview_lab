import math
import pytest

np = pytest.importorskip("numpy")


def test_two_step(submission):
    a, r = submission.gae(
        [1, 1], [0, 0], [0, 0], [False, True], [False, True], 0.9, 0.95
    )
    np.testing.assert_allclose(a, [1.855, 1])
    np.testing.assert_allclose(r, a)


def test_truncation_bootstraps(submission):
    np.testing.assert_allclose(
        submission.gae([1], [0], [5], [False], [True], 0.9)[0], [5.5]
    )


def test_termination_no_bootstrap(submission):
    np.testing.assert_allclose(
        submission.gae([1], [0], [5], [True], [True], 0.9)[0], [1]
    )


def test_no_cross_episode_leak(submission):
    np.testing.assert_allclose(
        submission.gae([1, 100], [0, 0], [5, 0], [False, True], [True, True], 0.9)[0],
        [5.5, 100],
    )


def test_invalid_final_boundary(submission):
    with pytest.raises(ValueError):
        submission.gae([1], [0], [0], [False], [False])


def test_zero_lambda(submission):
    np.testing.assert_allclose(
        submission.gae(
            [1, 2], [0.5, 0.5], [3, 4], [False, True], [False, True], 0.9, 0
        )[0],
        [3.2, 1.5],
    )
