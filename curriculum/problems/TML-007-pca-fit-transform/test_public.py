import math
import pytest

np = pytest.importorskip("numpy")


def test_rank_one_reconstruction(submission):
    x = np.array([[0.0, 0.0], [1, 2], [2, 4], [3, 6]])
    f = submission.fit_pca(x, 1)
    z = submission.transform_pca(x, f)
    np.testing.assert_allclose(submission.inverse_transform_pca(z, f), x, atol=1e-12)


def test_constant_ratio_zero(submission):
    f = submission.fit_pca(np.ones((4, 2)), 1)
    np.testing.assert_array_equal(f[3], [0])


def test_test_batch_not_recentered(submission):
    f = submission.fit_pca(np.array([[0.0, 0.0], [2.0, 0.0]]), 1)
    z = submission.transform_pca(np.array([[3.0, 0.0]]), f)
    assert abs(z[0, 0]) == pytest.approx(2)


def test_variance_denominator(submission):
    f = submission.fit_pca(np.array([[0.0], [2.0]]), 1)
    assert f[2][0] == pytest.approx(2)


def test_invalid_k(submission):
    with pytest.raises(ValueError):
        submission.fit_pca(np.ones((2, 3)), 3)
