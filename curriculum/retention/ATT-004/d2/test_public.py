import math
import pytest
import torch


def reference(q, k, v, heads):
    batch, q_len, hidden = q.shape; k_len = k.shape[1]; head_dim = hidden // heads; value_dim = v.shape[-1] // heads
    qh = q.reshape(batch, q_len, heads, head_dim).transpose(1, 2)
    kh = k.reshape(batch, k_len, heads, head_dim).transpose(1, 2)
    vh = v.reshape(batch, k_len, heads, value_dim).transpose(1, 2)
    probs = torch.softmax(qh @ kh.transpose(-2, -1) / math.sqrt(head_dim), -1)
    out = (probs @ vh).transpose(1, 2).contiguous().reshape(batch, q_len, heads * value_dim)
    return out, probs


def test_output_and_probabilities_match_reference(submission):
    q = torch.randn(2, 3, 8, dtype=torch.float64); k = torch.randn(2, 5, 8, dtype=torch.float64); v = torch.randn(2, 5, 12, dtype=torch.float64)
    actual_out, actual_probs = submission.attention_with_probabilities(q, k, v, 4)
    expected_out, expected_probs = reference(q, k, v, 4)
    assert torch.allclose(actual_out, expected_out, atol=1e-10) and torch.allclose(actual_probs, expected_probs, atol=1e-10)


def test_probability_shape_and_sum(submission):
    _, probs = submission.attention_with_probabilities(torch.randn(1, 2, 6), torch.randn(1, 4, 6), torch.randn(1, 4, 9), 3)
    assert probs.shape == (1, 3, 2, 4) and torch.allclose(probs.sum(-1), torch.ones(1, 3, 2))


def test_gradients_reach_all_inputs(submission):
    q = torch.randn(1, 2, 4, requires_grad=True); k = torch.randn(1, 3, 4, requires_grad=True); v = torch.randn(1, 3, 6, requires_grad=True)
    output, probabilities = submission.attention_with_probabilities(q, k, v, 2)
    (output.sum() + probabilities.square().sum()).backward()
    assert all(value.grad is not None for value in (q, k, v))


@pytest.mark.parametrize("q,k,v,h", [(torch.randn(2, 3), torch.randn(2, 3), torch.randn(2, 3), 1), (torch.randn(1, 2, 5), torch.randn(1, 2, 5), torch.randn(1, 2, 4), 2), (torch.randn(1, 2, 4), torch.randn(1, 3, 4), torch.randn(1, 2, 4), 2)])
def test_invalid_shapes(submission, q, k, v, h):
    with pytest.raises(ValueError):
        submission.attention_with_probabilities(q, k, v, h)


def test_non_contiguous_and_no_mutation(submission):
    q = torch.randn(1, 4, 8)[:, ::2]; k = torch.randn(1, 3, 8); v = torch.randn(1, 3, 8)
    before = q.clone()
    output, _ = submission.attention_with_probabilities(q, k, v, 2)
    assert output.shape == (1, 2, 8) and torch.equal(q, before)
