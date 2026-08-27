import pytest
import torch
import torch.nn.functional as F


def reference(logits, targets, mask):
    losses = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1), reduction="none").reshape_as(targets)
    return losses[mask].mean()


def test_matches_masked_framework_reference(submission):
    logits = torch.randn(2, 4, 5, dtype=torch.float64)
    targets = torch.randint(5, (2, 4))
    mask = torch.tensor([[True, True, False, False], [True, False, True, True]])
    assert torch.allclose(submission.masked_token_cross_entropy(logits, targets, mask), reference(logits, targets, mask), atol=1e-10)


def test_padding_targets_are_ignored_by_mask(submission):
    logits = torch.randn(1, 3, 4)
    targets = torch.tensor([[1, 999, 2]])
    mask = torch.tensor([[True, False, True]])
    assert torch.isfinite(submission.masked_token_cross_entropy(logits, targets, mask))


def test_gradient_only_for_selected_tokens(submission):
    logits = torch.randn(1, 3, 4, requires_grad=True)
    submission.masked_token_cross_entropy(logits, torch.tensor([[0, 1, 2]]), torch.tensor([[True, False, True]])).backward()
    assert logits.grad is not None and torch.count_nonzero(logits.grad[0, 1]).item() == 0


@pytest.mark.parametrize("targets,mask", [(torch.tensor([[0, 1]]), torch.tensor([[False, False]])), (torch.tensor([[0.0, 1.0]]), torch.tensor([[True, True]])), (torch.tensor([[0, 1]]), torch.ones(1, 2))])
def test_invalid_contract(submission, targets, mask):
    with pytest.raises(ValueError):
        submission.masked_token_cross_entropy(torch.randn(1, 2, 3), targets, mask)


def test_extreme_values_non_contiguous_and_no_mutation(submission):
    base = torch.tensor([[[10000.0, -10000.0], [9999.0, 9998.0], [5.0, 3.0]]])
    logits = base.transpose(1, 2)
    before = logits.clone()
    result = submission.masked_token_cross_entropy(logits, torch.tensor([[0, 1]]), torch.tensor([[True, True]]))
    assert torch.isfinite(result) and torch.equal(logits, before)
