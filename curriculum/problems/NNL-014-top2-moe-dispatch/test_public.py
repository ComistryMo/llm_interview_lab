import math
import pytest

torch = pytest.importorskip("torch")


def test_identity_experts(submission):
    x = torch.randn(4, 3)
    y, ids, g = submission.top2_moe(x, torch.randn(4, 3), [lambda v: v] * 3)
    torch.testing.assert_close(y, x)
    torch.testing.assert_close(g.sum(1), torch.ones(4))


def test_weighted_combine(submission):
    y, ids, g = submission.top2_moe(
        torch.tensor([[2.0]]),
        torch.log(torch.tensor([[0.25, 0.75]])),
        [lambda x: x, lambda x: 2 * x],
    )
    assert y.item() == pytest.approx(3.5)


def test_tie_expert_id(submission):
    _, ids, _ = submission.top2_moe(
        torch.ones(2, 1), torch.zeros(2, 3), [lambda x: x] * 3
    )
    assert ids.tolist() == [[0, 1], [0, 1]]


def test_empty_expert_not_called(submission):
    def forbidden(x):
        raise AssertionError("no tokens assigned")

    submission.top2_moe(
        torch.ones(2, 1),
        torch.tensor([[3.0, 2.0, 0.0]] * 2),
        [lambda x: x, lambda x: x, forbidden],
    )


def test_permutation_equivariance(submission):
    x = torch.randn(4, 2)
    r = torch.randn(4, 3)
    perm = torch.tensor([3, 0, 1, 2])
    f = [lambda v: v, lambda v: v * 2, lambda v: v * 3]
    a = submission.top2_moe(x, r, f)[0]
    b = submission.top2_moe(x[perm], r[perm], f)[0]
    torch.testing.assert_close(a[perm], b)
