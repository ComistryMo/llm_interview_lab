import math

import pytest

torch = pytest.importorskip("torch")


def _reference(logits, dim, keepdim=False):
    return torch.logsumexp(logits, dim=dim, keepdim=keepdim) - math.log(logits.shape[dim])


def test_matches_framework_identity(submission):
    logits = torch.randn(2, 3, 4, dtype=torch.float64)
    actual = submission.stable_logmeanexp(logits, dim=1)
    expected = _reference(logits, 1)
    assert actual.shape == (2, 4)
    assert torch.allclose(actual, expected, atol=1e-12, rtol=1e-10)


def test_keepdim_preserves_reduced_axis(submission):
    logits = torch.randn(2, 3, 4)
    actual = submission.stable_logmeanexp(logits, dim=-1, keepdim=True)
    assert actual.shape == (2, 3, 1)
    assert torch.allclose(actual, _reference(logits, -1, True))


@pytest.mark.parametrize("offset", [10000.0, -10000.0])
def test_extreme_finite_values_remain_finite(submission, offset):
    logits = torch.tensor([[offset, offset + 1.0, offset - 2.0]])
    actual = submission.stable_logmeanexp(logits)
    assert torch.isfinite(actual).all()
    assert torch.allclose(actual, _reference(logits, -1), atol=1e-4, rtol=1e-5)


def test_gradient_matches_framework_reference(submission):
    logits = torch.randn(2, 4, dtype=torch.float64, requires_grad=True)
    reference_logits = logits.detach().clone().requires_grad_()
    submission.stable_logmeanexp(logits, 0).sum().backward()
    _reference(reference_logits, 0).sum().backward()
    assert torch.allclose(logits.grad, reference_logits.grad, atol=1e-11, rtol=1e-10)


def test_supports_non_contiguous_input_without_mutation(submission):
    logits = torch.randn(3, 5, dtype=torch.float64).transpose(0, 1)
    before = logits.clone()
    actual = submission.stable_logmeanexp(logits, 0)
    assert actual.dtype == logits.dtype and actual.device == logits.device
    assert torch.allclose(actual, _reference(logits, 0), atol=1e-12)
    assert torch.equal(logits, before)


@pytest.mark.parametrize(
    "logits,dim,keepdim",
    [
        (torch.ones(2, 3, dtype=torch.long), 0, False),
        (torch.empty(2, 0), 1, False),
        (torch.ones(2, 3), 2, False),
        (torch.ones(2, 3), True, False),
        (torch.ones(2, 3), 0, 1),
    ],
)
def test_rejects_invalid_contract(submission, logits, dim, keepdim):
    with pytest.raises(ValueError):
        submission.stable_logmeanexp(logits, dim, keepdim)
