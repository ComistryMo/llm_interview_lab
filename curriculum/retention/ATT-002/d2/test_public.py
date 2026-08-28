import math

import pytest

torch = pytest.importorskip("torch")


def _reference(query, key, value, lengths):
    scores = query @ key.transpose(-2, -1) / math.sqrt(query.shape[-1])
    positions = torch.arange(key.shape[1], device=key.device)
    allowed = positions.unsqueeze(0) < lengths.unsqueeze(1)
    scores = scores.masked_fill(~allowed.unsqueeze(1), float("-inf"))
    probabilities = torch.softmax(scores, dim=-1)
    return probabilities @ value, probabilities


def test_variable_prefixes_match_reference(submission):
    torch.manual_seed(20)
    query = torch.randn(3, 4, 5, dtype=torch.float64)
    key = torch.randn(3, 6, 5, dtype=torch.float64)
    value = torch.randn(3, 6, 7, dtype=torch.float64)
    lengths = torch.tensor([6, 3, 1])
    output, probabilities = submission.length_masked_attention(
        query, key, value, lengths
    )
    expected_output, expected_probabilities = _reference(
        query, key, value, lengths
    )
    assert output.shape == (3, 4, 7)
    assert probabilities.shape == (3, 4, 6)
    assert torch.allclose(output, expected_output, atol=1e-10)
    assert torch.allclose(probabilities, expected_probabilities, atol=1e-10)


def test_invalid_prefix_probabilities_are_exact_zero(submission):
    query = torch.randn(2, 3, 4)
    key = torch.randn(2, 5, 4)
    value = torch.randn(2, 5, 2)
    lengths = torch.tensor([2, 4])
    _, probabilities = submission.length_masked_attention(
        query, key, value, lengths
    )
    positions = torch.arange(5)
    invalid = positions.unsqueeze(0) >= lengths.unsqueeze(1)
    forbidden = probabilities.masked_select(invalid.unsqueeze(1))
    assert torch.equal(forbidden, torch.zeros_like(forbidden))
    assert torch.allclose(probabilities.sum(-1), torch.ones(2, 3))


def test_extreme_scores_remain_finite(submission):
    query = torch.tensor([[[1.0e4, -1.0e4]]])
    key = torch.tensor([[[1.0e4, -1.0e4], [-1.0e4, 1.0e4]]])
    value = torch.tensor([[[2.0], [9.0]]])
    output, probabilities = submission.length_masked_attention(
        query, key, value, torch.tensor([2])
    )
    assert torch.isfinite(output).all()
    assert torch.isfinite(probabilities).all()
    assert torch.allclose(output, torch.tensor([[[2.0]]]))


def test_gradients_align_with_reference(submission):
    torch.manual_seed(21)
    values = [
        torch.randn(2, 3, 4, dtype=torch.float64, requires_grad=True),
        torch.randn(2, 5, 4, dtype=torch.float64, requires_grad=True),
        torch.randn(2, 5, 6, dtype=torch.float64, requires_grad=True),
    ]
    copies = [value.detach().clone().requires_grad_() for value in values]
    lengths = torch.tensor([5, 3])
    actual = submission.length_masked_attention(*values, lengths)[0]
    expected = _reference(*copies, lengths)[0]
    actual.square().sum().backward()
    expected.square().sum().backward()
    for value, copy in zip(values, copies):
        assert torch.allclose(value.grad, copy.grad, atol=1e-10)


def test_non_contiguous_inputs_and_no_mutation(submission):
    query = torch.randn(2, 6, 4)[:, ::2]
    key = torch.randn(2, 8, 4)[:, ::2]
    value = torch.randn(2, 8, 3)[:, ::2]
    lengths = torch.tensor([4, 2])
    snapshots = [item.clone() for item in (query, key, value, lengths)]
    output, probabilities = submission.length_masked_attention(
        query, key, value, lengths
    )
    assert output.shape == (2, 3, 3)
    assert probabilities.shape == (2, 3, 4)
    assert all(
        torch.equal(item, before)
        for item, before in zip((query, key, value, lengths), snapshots)
    )


@pytest.mark.parametrize(
    "query,key,value,lengths",
    [
        (torch.zeros(2, 3), torch.zeros(2, 3, 4), torch.zeros(2, 3, 4), torch.tensor([3, 3])),
        (torch.zeros(2, 3, 4), torch.zeros(3, 3, 4), torch.zeros(2, 3, 4), torch.tensor([3, 3])),
        (torch.zeros(2, 3, 4), torch.zeros(2, 3, 5), torch.zeros(2, 3, 4), torch.tensor([3, 3])),
        (torch.zeros(2, 3, 4), torch.zeros(2, 5, 4), torch.zeros(2, 3, 4), torch.tensor([3, 3])),
        (torch.zeros(2, 3, 4), torch.zeros(2, 3, 4), torch.zeros(2, 3, 4), torch.tensor([3])),
        (torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.tensor([0])),
        (torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.tensor([3])),
        (torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.zeros(1, 2, 3), torch.tensor([True])),
    ],
)
def test_invalid_contract_raises_value_error(
    submission, query, key, value, lengths
):
    with pytest.raises(ValueError):
        submission.length_masked_attention(query, key, value, lengths)


def test_dtype_or_device_mismatch_raises_value_error(submission):
    query = torch.zeros(1, 2, 3, dtype=torch.float32)
    key = torch.zeros(1, 2, 3, dtype=torch.float64)
    value = torch.zeros(1, 2, 3, dtype=torch.float32)
    with pytest.raises(ValueError):
        submission.length_masked_attention(query, key, value, torch.tensor([2]))
