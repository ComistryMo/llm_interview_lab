import pytest
import torch


def test_supports_non_prefix_masks(submission):
    hidden = torch.arange(30.0).reshape(2, 5, 3)
    mask = torch.tensor([[True, False, True, False, False], [False, True, False, False, True]])
    assert torch.equal(submission.last_true_token(hidden, mask), torch.stack((hidden[0, 2], hidden[1, 4])))


def test_preserves_gradient(submission):
    hidden = torch.randn(2, 3, 2, requires_grad=True)
    result = submission.last_true_token(hidden, torch.tensor([[1, 0, 0], [0, 1, 0]], dtype=torch.bool))
    result.square().sum().backward()
    assert hidden.grad is not None and torch.count_nonzero(hidden.grad).item() <= 4


def test_non_contiguous_hidden(submission):
    hidden = torch.randn(2, 4, 6)[..., ::2]
    result = submission.last_true_token(hidden, torch.tensor([[1, 0, 1, 0], [0, 1, 0, 0]], dtype=torch.bool))
    assert result.shape == (2, 3)


@pytest.mark.parametrize("mask", [torch.ones(2, 3), torch.tensor([[1, 0, 0]], dtype=torch.bool), torch.tensor([[0, 0, 0], [1, 0, 0]], dtype=torch.bool)])
def test_invalid_masks(submission, mask):
    with pytest.raises(ValueError):
        submission.last_true_token(torch.randn(2, 3, 4), mask)


def test_inputs_are_not_mutated(submission):
    hidden = torch.randn(1, 2, 3)
    mask = torch.tensor([[True, False]])
    before = hidden.clone()
    submission.last_true_token(hidden, mask)
    assert torch.equal(hidden, before) and torch.equal(mask, torch.tensor([[True, False]]))
