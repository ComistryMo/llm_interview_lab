import pytest
import torch


def test_gathers_last_length_position(submission):
    hidden = torch.arange(24.0).reshape(2, 3, 4)
    result = submission.token_at_lengths(hidden, torch.tensor([1, 3]))
    assert torch.equal(result, torch.stack((hidden[0, 0], hidden[1, 2])))


def test_preserves_dtype_device_and_gradient(submission):
    hidden = torch.randn(2, 4, 3, dtype=torch.float64, requires_grad=True)
    result = submission.token_at_lengths(hidden, torch.tensor([2, 4]))
    assert result.dtype == hidden.dtype and result.device == hidden.device
    result.sum().backward()
    assert hidden.grad is not None and hidden.grad.abs().sum() == 6


def test_supports_non_contiguous_hidden(submission):
    base = torch.randn(2, 5, 6)
    hidden = base[..., ::2]
    assert not hidden.is_contiguous()
    assert torch.equal(submission.token_at_lengths(hidden, torch.tensor([5, 1])), torch.stack((hidden[0, 4], hidden[1, 0])))


@pytest.mark.parametrize("lengths", [torch.tensor([0, 2]), torch.tensor([1, 4]), torch.tensor([1.0, 2.0])])
def test_invalid_lengths(submission, lengths):
    with pytest.raises(ValueError):
        submission.token_at_lengths(torch.randn(2, 3, 4), lengths)


def test_does_not_mutate_inputs(submission):
    hidden = torch.randn(2, 3, 4)
    lengths = torch.tensor([2, 1])
    before = hidden.clone()
    submission.token_at_lengths(hidden, lengths)
    assert torch.equal(hidden, before) and torch.equal(lengths, torch.tensor([2, 1]))
