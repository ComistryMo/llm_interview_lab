import pytest
import torch


def reference(logits, mask, dim):
    masked = logits.masked_fill(~mask, float("-inf"))
    return torch.softmax(masked, dim=dim).masked_fill(~mask, 0)


def test_masked_probabilities_match_reference(submission):
    logits = torch.tensor([[1.0, 9.0, 2.0], [3.0, 4.0, 5.0]])
    mask = torch.tensor([[True, False, True], [False, True, True]])
    assert torch.allclose(submission.masked_softmax(logits, mask), reference(logits, mask, -1))


def test_masked_positions_are_exact_zero_and_rows_sum_one(submission):
    mask = torch.tensor([[True, False, True]])
    result = submission.masked_softmax(torch.randn(1, 3), mask)
    assert result[0, 1].item() == 0 and torch.allclose(result.sum(-1), torch.ones(1))


def test_extreme_values_and_gradient(submission):
    logits = torch.tensor([[10000.0, -10000.0, 9999.0]], requires_grad=True)
    result = submission.masked_softmax(logits, torch.tensor([[True, False, True]]))
    assert torch.isfinite(result).all()
    result[0, 2].backward()
    assert torch.isfinite(logits.grad).all() and logits.grad[0, 1] == 0


@pytest.mark.parametrize("mask", [torch.tensor([[False, False]]), torch.ones(1, 2), torch.tensor([True, False, True])])
def test_invalid_masks(submission, mask):
    with pytest.raises(ValueError):
        submission.masked_softmax(torch.randn(1, 2), mask)


def test_broadcast_mask_and_input_immutability(submission):
    logits = torch.randn(2, 3, 4)
    mask = torch.tensor([[[True, True, False, True]], [[True, False, True, True]]])
    before = logits.clone()
    result = submission.masked_softmax(logits, mask, -1)
    assert result.shape == logits.shape and torch.equal(logits, before)
