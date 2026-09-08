import math
import pytest

torch = pytest.importorskip("torch")


def constant_weights():
    return torch.zeros(1, 8), torch.zeros(1), torch.zeros(1, 1), torch.ones(1)


def test_constant_one_is_sum_not_mean(submission):
    q = torch.ones(1, 2)
    h = torch.tensor([[[1.0, 2.0], [3.0, 4.0]]])
    y, a = submission.din_interest(
        q, h, torch.ones(1, 2, dtype=torch.bool), *constant_weights()
    )
    torch.testing.assert_close(y, torch.tensor([[4.0, 6.0]]))


def test_all_padding_zero(submission):
    y, a = submission.din_interest(
        torch.ones(1, 2),
        torch.ones(1, 3, 2),
        torch.zeros(1, 3, dtype=torch.bool),
        *constant_weights(),
    )
    assert y.abs().sum() == 0 and a.abs().sum() == 0


def test_padding_ignored(submission):
    y, _ = submission.din_interest(
        torch.ones(1, 2),
        torch.tensor([[[2.0, 3.0], [100.0, 100.0]]]),
        torch.tensor([[True, False]]),
        *constant_weights(),
    )
    torch.testing.assert_close(y, torch.tensor([[2.0, 3.0]]))


def test_history_permutation(submission):
    q = torch.randn(2, 2)
    h = torch.randn(2, 4, 2)
    valid = torch.tensor([[True, False, True, True]] * 2)
    args = (torch.randn(3, 8), torch.randn(3), torch.randn(1, 3), torch.randn(1))
    p = torch.tensor([2, 0, 3, 1])
    a, _ = submission.din_interest(q, h, valid, *args)
    b, _ = submission.din_interest(q, h[:, p], valid[:, p], *args)
    torch.testing.assert_close(a, b)


def test_feature_order(submission):
    q = torch.tensor([[2.0]])
    h = torch.tensor([[[3.0]]])
    w = torch.tensor([[0.0, 0.0, 0.0, 1.0]])
    y, a = submission.din_interest(
        q,
        h,
        torch.tensor([[True]]),
        w,
        torch.zeros(1),
        torch.ones(1, 1),
        torch.zeros(1),
    )
    assert a.item() == 6 and y.item() == 18
