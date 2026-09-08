import numpy as np
import pytest


def test_shared_weight_known_example(submission):
    dh, dw = submission.shared_embedding_projection_vjp(np.array([1, 1], dtype=np.int64), np.array([[2., -1.]]), np.array([[1., 2.], [3., 4.]]), np.array([[1., 0.], [2., 1.]]), np.array([[.5, 1.]]))
    np.testing.assert_allclose(dh, [[3.5, 5.]])
    np.testing.assert_allclose(dw, [[1., -.5], [5., 0.]])


def test_empty_and_different_leading_shapes(submission):
    ids, w = np.empty((2, 0), dtype=np.int64), np.ones((3, 2))
    dh, dw = submission.shared_embedding_projection_vjp(ids, np.empty((0, 2)), w, np.empty((2, 0, 2)), np.empty((0, 3)))
    assert dh.shape == (0, 2) and dw.shape == (3, 2) and not dw.any()
    dh, dw = submission.shared_embedding_projection_vjp(np.array([[1, 1]], dtype=np.int64), np.array([2., 3.]), w, np.ones((1, 2, 2)), np.zeros(3))
    np.testing.assert_array_equal(dh, [0., 0.])
    np.testing.assert_array_equal(dw, [[0., 0.], [2., 2.], [0., 0.]])


def test_linearity_noncontiguous_and_no_mutation(submission):
    rng = np.random.default_rng(7)
    ids = np.array([2, 0, 2], dtype=np.int64)
    h, w = rng.normal(size=(2, 4))[:, ::2], rng.normal(size=(3, 4))[:, ::2]
    ge, gl = rng.normal(size=(3, 2)), rng.normal(size=(2, 3))
    arrays = [ids, h, w, ge, gl]
    before = [a.copy() for a in arrays]
    both = submission.shared_embedding_projection_vjp(*arrays)
    first = submission.shared_embedding_projection_vjp(ids, h, w, ge, np.zeros_like(gl))
    second = submission.shared_embedding_projection_vjp(ids, h, w, np.zeros_like(ge), gl)
    for actual, a, b in zip(both, first, second):
        np.testing.assert_allclose(actual, a + b, atol=1e-12)
        assert actual.dtype == np.float64 and not any(np.shares_memory(actual, item) for item in arrays)
    for a, b in zip(arrays, before):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("bad", ["negative", "past_end", "embedding_shape", "logit_shape", "hidden_shape", "weight_shape", "scalar_ids"])
def test_invalid_shapes_and_indices(submission, bad):
    ids, h, w, ge, gl = np.array([0, 1], dtype=np.int64), np.ones((2, 3)), np.ones((4, 3)), np.ones((2, 3)), np.ones((2, 4))
    if bad == "negative": ids[0] = -1
    if bad == "past_end": ids[0] = 4
    if bad == "embedding_shape": ge = np.ones((1, 3))
    if bad == "logit_shape": gl = np.ones((4,))
    if bad == "hidden_shape": h = np.ones((2, 2))
    if bad == "weight_shape": w = np.ones((4, 3, 1))
    if bad == "scalar_ids": ids = np.array(1, dtype=np.int64)
    with pytest.raises(ValueError):
        submission.shared_embedding_projection_vjp(ids, h, w, ge, gl)
