import math
import pytest
import torch


def reference(q, k, v, heads, padding):
    batch, q_len, hidden = q.shape; k_len = k.shape[1]; dim = hidden // heads; value_dim = v.shape[-1] // heads
    qh = q.reshape(batch, q_len, heads, dim).transpose(1, 2); kh = k.reshape(batch, k_len, heads, dim).transpose(1, 2); vh = v.reshape(batch, k_len, heads, value_dim).transpose(1, 2)
    scores = qh @ kh.transpose(-2, -1) / math.sqrt(dim)
    causal = torch.arange(k_len, device=q.device)[None, :] <= torch.arange(q_len, device=q.device)[:, None]
    valid = causal[None, None] & padding[:, None, None, :]
    if not valid.any(-1).all(): raise ValueError
    return (torch.softmax(scores.masked_fill(~valid, float("-inf")), -1) @ vh).transpose(1, 2).contiguous().reshape(batch, q_len, heads * value_dim)


def test_matches_causal_padding_reference(submission):
    q = torch.randn(2, 4, 8, dtype=torch.float64); k = torch.randn(2, 4, 8, dtype=torch.float64); v = torch.randn(2, 4, 12, dtype=torch.float64)
    mask = torch.tensor([[True, True, True, False], [True, True, False, False]])
    assert torch.allclose(submission.causal_padded_attention(q, k, v, 4, mask), reference(q, k, v, 4, mask), atol=1e-10)


def test_future_and_padding_values_do_not_affect_earlier_output(submission):
    q = k = torch.zeros(1, 3, 4); v = torch.tensor([[[1., 2., 3., 4.], [5., 6., 7., 8.], [100., 200., 300., 400.]]])
    result = submission.causal_padded_attention(q, k, v, 2, torch.tensor([[True, True, False]]))
    assert torch.equal(result[0, 0], v[0, 0]) and torch.allclose(result[0, 1], v[0, :2].mean(0))


def test_gradient_dtype_and_device(submission):
    q = torch.randn(1, 3, 4, dtype=torch.float64, requires_grad=True); k = torch.randn(1, 3, 4, dtype=torch.float64, requires_grad=True); v = torch.randn(1, 3, 4, dtype=torch.float64, requires_grad=True)
    result = submission.causal_padded_attention(q, k, v, 2, torch.ones(1, 3, dtype=torch.bool)); result.sum().backward()
    assert result.dtype == q.dtype and result.device == q.device and all(x.grad is not None for x in (q, k, v))


@pytest.mark.parametrize("mask", [torch.ones(1, 3), torch.tensor([[False, True, True]]), torch.ones(2, 3, dtype=torch.bool)])
def test_invalid_padding_masks(submission, mask):
    with pytest.raises(ValueError):
        submission.causal_padded_attention(torch.randn(1, 3, 4), torch.randn(1, 3, 4), torch.randn(1, 3, 4), 2, mask)


def test_non_contiguous_and_no_mutation(submission):
    q = torch.randn(1, 6, 4)[:, ::2]; k = torch.randn(1, 3, 4); v = torch.randn(1, 3, 4); before = q.clone()
    assert submission.causal_padded_attention(q, k, v, 2, torch.ones(1, 3, dtype=torch.bool)).shape == q.shape
    assert torch.equal(q, before)
