import pytest
import torch
import torch.nn.functional as F


@pytest.mark.parametrize("batch,classes", [(1, 2), (4, 7), (3, 3)])
def test_matches_framework_reference(submission, batch, classes):
    logits = torch.randn(batch, classes, dtype=torch.float64)
    targets = torch.randint(classes, (batch,))
    result = submission.per_example_cross_entropy(logits, targets)
    assert result.shape == (batch,)
    assert torch.allclose(result, F.cross_entropy(logits, targets, reduction="none"), atol=1e-10)


def test_extreme_values_are_finite(submission):
    result = submission.per_example_cross_entropy(torch.tensor([[10000.0, -10000.0], [-9999.0, -10000.0]]), torch.tensor([0, 1]))
    assert torch.isfinite(result).all()


def test_gradient_matches_framework(submission):
    left = torch.randn(3, 5, dtype=torch.float64, requires_grad=True)
    right = left.detach().clone().requires_grad_()
    targets = torch.tensor([0, 3, 1])
    submission.per_example_cross_entropy(left, targets).sum().backward()
    F.cross_entropy(right, targets, reduction="sum").backward()
    assert torch.allclose(left.grad, right.grad, atol=1e-9)


@pytest.mark.parametrize("logits,targets", [(torch.randn(2, 3, 1), torch.tensor([0, 1])), (torch.randn(2, 3), torch.tensor([0.0, 1.0])), (torch.randn(2, 3), torch.tensor([0, 3]))])
def test_invalid_contract(submission, logits, targets):
    with pytest.raises(ValueError):
        submission.per_example_cross_entropy(logits, targets)


def test_non_contiguous_and_no_mutation(submission):
    logits = torch.randn(5, 3).t()
    targets = torch.tensor([0, 2, 4])
    before = logits.clone()
    assert submission.per_example_cross_entropy(logits, targets).shape == (3,)
    assert torch.equal(logits, before)
