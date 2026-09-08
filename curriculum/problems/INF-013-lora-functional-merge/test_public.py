import math
import pytest

torch = pytest.importorskip("torch")


def test_zero_b_equals_base(submission):
    x = torch.randn(2, 3)
    w = torch.randn(4, 3)
    bias = torch.randn(4)
    a = torch.randn(2, 3)
    b = torch.zeros(4, 2)
    torch.testing.assert_close(
        submission.lora_forward(x, w, bias, a, b), x @ w.T + bias
    )


def test_merge_equivalence(submission):
    x = torch.randn(2, 5, 3)
    w = torch.randn(4, 3)
    a = torch.randn(2, 3)
    b = torch.randn(4, 2)
    y = submission.lora_forward(x, w, None, a, b, 4)
    torch.testing.assert_close(y, x @ submission.merge_lora(w, a, b, 4).T)


def test_merge_not_accumulated(submission):
    w = torch.ones(2, 2)
    a = torch.ones(1, 2)
    b = torch.ones(2, 1)
    old = w.clone()
    first = submission.merge_lora(w, a, b)
    second = submission.merge_lora(w, a, b)
    torch.testing.assert_close(first, second)
    torch.testing.assert_close(w, old)


def test_frozen_base(submission):
    w = torch.ones(2, 2, requires_grad=True)
    bias = torch.ones(2, requires_grad=True)
    a = torch.ones(1, 2, requires_grad=True)
    b = torch.ones(2, 1, requires_grad=True)
    submission.lora_forward(torch.ones(1, 2), w, bias, a, b).sum().backward()
    assert w.grad is None and bias.grad is None
    assert a.grad is not None and b.grad is not None


def test_zero_b_initial_gradient(submission):
    a = torch.ones(1, 2, requires_grad=True)
    b = torch.zeros(2, 1, requires_grad=True)
    submission.lora_forward(
        torch.ones(1, 2), torch.ones(2, 2), None, a, b
    ).sum().backward()
    assert a.grad.abs().sum() == 0
    assert b.grad.abs().sum() > 0
