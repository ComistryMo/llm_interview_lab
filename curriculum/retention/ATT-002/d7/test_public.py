import math

import pytest

torch = pytest.importorskip("torch")


def _allowed(mask, query_length, past_length):
    query_positions = past_length + torch.arange(
        query_length, device=mask.device
    )
    key_positions = torch.arange(mask.shape[1], device=mask.device)
    causal = key_positions.unsqueeze(0) <= query_positions.unsqueeze(1)
    return mask[:, None, None, :] & causal[None, None, :, :]


def _reference(query, key, value, mask, past_length):
    allowed = _allowed(mask, query.shape[-2], past_length)
    scores = query @ key.transpose(-2, -1) / math.sqrt(query.shape[-1])
    probabilities = torch.softmax(
        scores.masked_fill(~allowed, float("-inf")), dim=-1
    )
    return probabilities @ value, probabilities, allowed


def test_rectangular_causal_attention_matches_reference(submission):
    torch.manual_seed(70)
    query = torch.randn(2, 3, 2, 4, dtype=torch.float64)
    key = torch.randn(2, 3, 5, 4, dtype=torch.float64)
    value = torch.randn(2, 3, 5, 6, dtype=torch.float64)
    mask = torch.tensor([[1, 1, 1, 1, 1], [0, 1, 1, 1, 1]], dtype=torch.bool)
    output, probabilities = submission.decoder_attention_with_padding(
        query, key, value, mask, 3
    )
    expected_output, expected_probabilities, _ = _reference(
        query, key, value, mask, 3
    )
    assert output.shape == (2, 3, 2, 6)
    assert probabilities.shape == (2, 3, 2, 5)
    assert torch.allclose(output, expected_output, atol=1e-10)
    assert torch.allclose(probabilities, expected_probabilities, atol=1e-10)


def test_padding_and_future_probabilities_are_exact_zero(submission):
    query = torch.randn(1, 2, 3, 4)
    key = torch.randn(1, 2, 5, 4)
    value = torch.randn(1, 2, 5, 3)
    mask = torch.tensor([[0, 1, 1, 1, 1]], dtype=torch.bool)
    _, probabilities = submission.decoder_attention_with_padding(
        query, key, value, mask, 2
    )
    allowed = _allowed(mask, 3, 2).expand_as(probabilities)
    assert torch.equal(
        probabilities.masked_select(~allowed),
        torch.zeros_like(probabilities.masked_select(~allowed)),
    )
    assert torch.allclose(probabilities.sum(-1), torch.ones(1, 2, 3))


def test_prefill_contract_is_the_square_causal_case(submission):
    query = torch.randn(1, 1, 4, 3)
    key = torch.randn(1, 1, 4, 3)
    value = torch.randn(1, 1, 4, 2)
    mask = torch.ones(1, 4, dtype=torch.bool)
    _, probabilities = submission.decoder_attention_with_padding(
        query, key, value, mask, 0
    )
    assert torch.equal(
        torch.triu(probabilities, diagonal=1),
        torch.zeros_like(probabilities),
    )


def test_gradients_align_with_reference(submission):
    torch.manual_seed(71)
    tensors = [
        torch.randn(1, 2, 2, 3, dtype=torch.float64, requires_grad=True),
        torch.randn(1, 2, 4, 3, dtype=torch.float64, requires_grad=True),
        torch.randn(1, 2, 4, 5, dtype=torch.float64, requires_grad=True),
    ]
    copies = [tensor.detach().clone().requires_grad_() for tensor in tensors]
    mask = torch.tensor([[1, 1, 1, 1]], dtype=torch.bool)
    actual = submission.decoder_attention_with_padding(*tensors, mask, 2)[0]
    expected = _reference(*copies, mask, 2)[0]
    actual.square().sum().backward()
    expected.square().sum().backward()
    for tensor, copy in zip(tensors, copies):
        assert torch.allclose(tensor.grad, copy.grad, atol=1e-10)


def test_non_contiguous_inputs_are_supported_without_mutation(submission):
    query = torch.randn(1, 2, 4, 3)[:, :, ::2]
    key = torch.randn(1, 2, 8, 3)[:, :, ::2]
    value = torch.randn(1, 2, 8, 5)[:, :, ::2]
    mask = torch.tensor([[1, 1, 1, 1]], dtype=torch.bool)
    snapshots = [item.clone() for item in (query, key, value, mask)]
    output, _ = submission.decoder_attention_with_padding(
        query, key, value, mask, 2
    )
    assert output.shape == (1, 2, 2, 5)
    assert all(
        torch.equal(item, before)
        for item, before in zip((query, key, value, mask), snapshots)
    )


@pytest.mark.parametrize(
    "query,key,value,mask,past",
    [
        (torch.zeros(1, 2, 3), torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.ones(1, 2, dtype=torch.bool), 0),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 2, 2, 3), torch.zeros(1, 1, 2, 3), torch.ones(1, 2, dtype=torch.bool), 0),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 4), torch.zeros(1, 1, 2, 3), torch.ones(1, 2, dtype=torch.bool), 0),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 3, 3), torch.zeros(1, 1, 2, 3), torch.ones(1, 3, dtype=torch.bool), 1),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.ones(1, 2), 0),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.zeros(1, 2, dtype=torch.bool), 0),
        (torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.zeros(1, 1, 2, 3), torch.ones(1, 2, dtype=torch.bool), True),
    ],
)
def test_invalid_contract_raises_value_error(
    submission, query, key, value, mask, past
):
    with pytest.raises(ValueError):
        submission.decoder_attention_with_padding(
            query, key, value, mask, past
        )
