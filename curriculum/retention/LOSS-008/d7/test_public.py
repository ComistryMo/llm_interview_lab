import pytest

torch = pytest.importorskip("torch")


def _reference(logits, mask, dim, keepdim=False):
    return torch.logsumexp(logits.masked_fill(~mask, -torch.inf), dim=dim, keepdim=keepdim)


def test_matches_masked_framework_reference(submission):
    logits = torch.tensor([[1.0, 2.0, 9.0], [-1.0, 4.0, 3.0]], dtype=torch.float64)
    mask = torch.tensor([[True, True, False], [True, False, True]])
    actual = submission.masked_logsumexp(logits, mask, dim=-1)
    assert actual.shape == (2,)
    assert torch.allclose(actual, _reference(logits, mask, -1), atol=1e-12)


def test_keepdim_and_nonfinal_reduction(submission):
    logits = torch.randn(2, 3, 4, dtype=torch.float64)
    mask = torch.tensor(
        [
            [[1, 0, 1, 0], [1, 1, 0, 0], [0, 1, 1, 1]],
            [[1, 1, 0, 1], [0, 1, 1, 0], [1, 0, 1, 1]],
        ],
        dtype=torch.bool,
    )
    actual = submission.masked_logsumexp(logits, mask, dim=1, keepdim=True)
    assert actual.shape == (2, 1, 4)
    assert torch.allclose(actual, _reference(logits, mask, 1, True), atol=1e-12)


def test_extreme_values_remain_finite(submission):
    logits = torch.tensor([[10000.0, -10000.0, 9999.0], [-9999.0, -10000.0, 10000.0]])
    mask = torch.tensor([[True, False, True], [True, True, False]])
    actual = submission.masked_logsumexp(logits, mask)
    assert torch.isfinite(actual).all()
    assert torch.allclose(actual, _reference(logits, mask, -1), atol=1e-4, rtol=1e-5)


def test_gradient_matches_reference_and_masked_positions_receive_zero(submission):
    logits = torch.randn(2, 4, dtype=torch.float64, requires_grad=True)
    reference_logits = logits.detach().clone().requires_grad_()
    mask = torch.tensor([[True, False, True, True], [False, True, True, False]])
    submission.masked_logsumexp(logits, mask, -1).sum().backward()
    _reference(reference_logits, mask, -1).sum().backward()
    assert torch.allclose(logits.grad, reference_logits.grad, atol=1e-11)
    assert torch.equal(logits.grad[~mask], torch.zeros_like(logits.grad[~mask]))


def test_supports_non_contiguous_inputs_without_mutation(submission):
    logits = torch.randn(3, 4, dtype=torch.float64).transpose(0, 1)
    mask = torch.tensor(
        [[1, 1, 0, 1], [1, 0, 1, 1], [0, 1, 1, 1]], dtype=torch.bool
    ).transpose(0, 1)
    before_logits, before_mask = logits.clone(), mask.clone()
    actual = submission.masked_logsumexp(logits, mask, dim=0)
    assert actual.dtype == logits.dtype and actual.device == logits.device
    assert torch.allclose(actual, _reference(logits, mask, 0), atol=1e-12)
    assert torch.equal(logits, before_logits)
    assert torch.equal(mask, before_mask)


@pytest.mark.parametrize(
    "logits,mask,dim,keepdim",
    [
        (torch.ones(2, 3), torch.ones(2, 2, dtype=torch.bool), 1, False),
        (torch.ones(2, 3), torch.ones(2, 3), 1, False),
        (torch.ones(2, 3, dtype=torch.long), torch.ones(2, 3, dtype=torch.bool), 1, False),
        (torch.ones(2, 3), torch.tensor([[1, 0, 0], [0, 0, 0]], dtype=torch.bool), 1, False),
        (torch.ones(2, 3), torch.ones(2, 3, dtype=torch.bool), 2, False),
        (torch.ones(2, 3), torch.ones(2, 3, dtype=torch.bool), 1, 1),
    ],
)
def test_rejects_invalid_contract(submission, logits, mask, dim, keepdim):
    with pytest.raises(ValueError):
        submission.masked_logsumexp(logits, mask, dim, keepdim)
