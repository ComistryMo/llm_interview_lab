import numpy as np
import pytest


def test_known_example(submission):
    dx, dw, db = submission.accumulate_linear_vjp([(np.array([[1., 3.], [2., 5.]]), np.array([[.5], [1.5]]))], np.array([[2., -1.]]))
    np.testing.assert_allclose(dx[0], [[1., -.5], [3., -1.5]])
    np.testing.assert_allclose(dw, [[3.5, 9.]])
    np.testing.assert_allclose(db, [2.])


def test_empty_chunks_and_zero_length_batch(submission):
    w = np.ones((3, 2))
    dx, dw, db = submission.accumulate_linear_vjp([], w)
    assert dx == [] and dw.shape == (3, 2) and db.shape == (3,)
    assert not dw.any() and not db.any()
    dx, dw, db = submission.accumulate_linear_vjp([(np.zeros((2, 0, 2)), np.zeros((2, 0, 3)))], w)
    assert dx[0].shape == (2, 0, 2) and not dw.any() and not db.any()


def test_split_batches_preserve_sums_and_inputs(submission):
    rng = np.random.default_rng(18)
    x, g, w = rng.normal(size=(6, 4))[:, ::2], rng.normal(size=(6, 6))[:, ::2], rng.normal(size=(3, 2))
    before = [a.copy() for a in (x, g, w)]
    whole = submission.accumulate_linear_vjp([(x, g)], w)
    split = submission.accumulate_linear_vjp([(x[:1], g[:1]), (x[1:5].reshape(2, 2, 2), g[1:5].reshape(2, 2, 3)), (x[5], g[5])], w)
    for left, right in zip(whole[1:], split[1:]):
        np.testing.assert_allclose(left, right, atol=1e-12)
    np.testing.assert_allclose(whole[0][0], np.concatenate([a.reshape(-1, 2) for a in split[0]]))
    for actual, expected in zip((x, g, w), before):
        np.testing.assert_array_equal(actual, expected)
    for output in [*split[0], *split[1:]]:
        assert output.dtype == np.float64
        assert not any(np.shares_memory(output, item) for item in (x, g, w))


@pytest.mark.parametrize("xshape,gshape,wshape", [((2, 2), (1, 3), (3, 2)), ((2,), (2,), (3, 2)), ((), (3,), (3, 2)), ((2,), (3,), (3, 2, 1)), ((0,), (3,), (3, 0))])
def test_shape_errors(submission, xshape, gshape, wshape):
    with pytest.raises(ValueError):
        submission.accumulate_linear_vjp([(np.zeros(xshape), np.zeros(gshape))], np.zeros(wshape))
