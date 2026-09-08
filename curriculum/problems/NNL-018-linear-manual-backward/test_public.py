import pytest

np = pytest.importorskip("numpy")


def test_vector_with_nonuniform_upstream(submission):
    dx, dw, db = submission.linear_backward(np.array([2., 3.]), np.array([[1., 4.], [5., 2.]]), np.array([7., 11.]))
    np.testing.assert_allclose(dx, [62., 50.])
    np.testing.assert_allclose(dw, [[14., 21.], [22., 33.]])
    np.testing.assert_allclose(db, [7., 11.])


def test_sequence_accumulates_without_extra_average(submission):
    x = np.ones((2, 3, 4))
    dx, dw, db = submission.linear_backward(x, np.ones((5, 4)), np.ones((2, 3, 5)))
    np.testing.assert_allclose(dx, np.full_like(x, 5))
    np.testing.assert_allclose(dw, np.full((5, 4), 6.))
    np.testing.assert_allclose(db, np.full(5, 6.))


def test_no_bias_and_noncontiguous_input(submission):
    x = np.arange(24.).reshape(4, 6)[:, ::2]
    before = x.copy()
    dx, dw, db = submission.linear_backward(x, np.eye(3), np.ones_like(x), bias=False)
    np.testing.assert_allclose(dx, 1.)
    np.testing.assert_allclose(dw, np.tile(x.sum(0), (3, 1)))
    assert db is None
    np.testing.assert_array_equal(x, before)


def test_empty_batch_returns_zero_parameter_gradients(submission):
    dx, dw, db = submission.linear_backward(np.zeros((2, 0, 3)), np.ones((4, 3)), np.zeros((2, 0, 4)))
    assert dx.shape == (2, 0, 3) and dw.shape == (4, 3) and db.shape == (4,)
    assert not dw.any() and not db.any()


@pytest.mark.parametrize("x,w,g", [(np.ones((2, 3)), np.ones((4, 3)), np.ones((1, 4))), (np.ones((2, 3)), np.ones((4, 2)), np.ones((2, 4))), (np.ones(3), np.ones(3), np.ones(3))])
def test_shape_mismatch_is_rejected(submission, x, w, g):
    with pytest.raises(ValueError):
        submission.linear_backward(x, w, g)
