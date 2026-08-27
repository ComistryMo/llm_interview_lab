import pytest
import torch
import torch.nn.functional as F


@pytest.mark.parametrize("shape,dim", [((2, 3), -1), ((2, 3, 4), 1), ((5,), 0)])
def test_matches_framework_reference(submission, shape, dim):
    logits = torch.randn(*shape, dtype=torch.float64)
    actual = submission.stable_log_softmax(logits, dim)
    assert torch.allclose(actual, F.log_softmax(logits, dim=dim), atol=1e-10, rtol=1e-8)


def test_extreme_values_are_finite(submission):
    logits = torch.tensor([[10000.0, 9999.0, -10000.0]])
    result = submission.stable_log_softmax(logits)
    assert torch.isfinite(result).all()


def test_probability_invariant(submission):
    result = submission.stable_log_softmax(torch.randn(3, 7), 1)
    assert torch.allclose(result.exp().sum(1), torch.ones(3), atol=1e-6)


def test_gradient_matches_reference(submission):
    left = torch.randn(2, 4, dtype=torch.float64, requires_grad=True)
    right = left.detach().clone().requires_grad_()
    submission.stable_log_softmax(left, -1).square().sum().backward()
    F.log_softmax(right, -1).square().sum().backward()
    assert torch.allclose(left.grad, right.grad, atol=1e-9)


def test_non_contiguous_and_no_mutation(submission):
    logits = torch.randn(3, 4).t()
    before = logits.clone()
    result = submission.stable_log_softmax(logits, 0)
    assert result.shape == logits.shape and torch.equal(logits, before)
