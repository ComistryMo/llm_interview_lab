import math
import pytest

np = pytest.importorskip("numpy")


def inputs():
    rng = np.random.default_rng(9)
    return (
        rng.normal(size=(4, 3)),
        np.array([0, 1, 0, 1]),
        [
            rng.normal(scale=0.1, size=(3, 5)),
            np.ones(5),
            rng.normal(scale=0.1, size=(5, 2)),
            np.zeros(2),
        ],
    )


def test_uniform_logits(submission):
    x, y, p = inputs()
    p[2][:] = 0
    p[3][:] = 0
    loss, g = submission.mlp_loss_grads(x, y, p)
    assert loss == pytest.approx(math.log(2))


def test_gradient_shapes(submission):
    x, y, p = inputs()
    _, g = submission.mlp_loss_grads(x, y, p)
    assert [a.shape for a in g] == [a.shape for a in p]


def test_duplicate_batch(submission):
    x, y, p = inputs()
    a, g = submission.mlp_loss_grads(x, y, p)
    b, h = submission.mlp_loss_grads(np.tile(x, (2, 1)), np.tile(y, 2), p)
    assert a == pytest.approx(b)
    for u, v in zip(g, h):
        np.testing.assert_allclose(u, v, atol=1e-12)


def test_one_update_descends(submission):
    x, y, p = inputs()
    a, g = submission.mlp_loss_grads(x, y, p)
    new = [v - 0.01 * d for v, d in zip(p, g)]
    assert submission.mlp_loss_grads(x, y, new)[0] < a


def test_no_parameter_mutation(submission):
    x, y, p = inputs()
    old = [v.copy() for v in p]
    submission.mlp_loss_grads(x, y, p)
    for a, b in zip(p, old):
        np.testing.assert_array_equal(a, b)
