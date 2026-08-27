import pytest

torch = pytest.importorskip("torch")
F = torch.nn.functional


def _reference(hidden, mask, weight, bias, targets):
    positions = torch.arange(hidden.shape[1], device=hidden.device).expand_as(mask)
    indices = positions.masked_fill(~mask, -1).max(dim=1).values
    selected = hidden[torch.arange(hidden.shape[0], device=hidden.device), indices]
    logits = selected @ weight.t() + bias
    return logits, F.cross_entropy(logits, targets), logits.argmax(dim=-1)


def test_right_padding_matches_reference(submission):
    hidden = torch.arange(24.0, dtype=torch.float64).reshape(2, 3, 4)
    mask = torch.tensor([[1, 1, 0], [1, 1, 1]], dtype=torch.bool)
    weight = torch.randn(3, 4, dtype=torch.float64)
    bias = torch.randn(3, dtype=torch.float64)
    targets = torch.tensor([1, 2])
    actual = submission.masked_sequence_classification_loss(hidden, mask, weight, bias, targets)
    expected = _reference(hidden, mask, weight, bias, targets)
    assert all(torch.allclose(a, e, atol=1e-10) for a, e in zip(actual[:2], expected[:2]))
    assert torch.equal(actual[2], expected[2])


def test_left_padding_and_gapped_mask_select_greatest_true_position(submission):
    hidden = torch.arange(30.0).reshape(2, 5, 3)
    mask = torch.tensor([[0, 1, 1, 0, 0], [1, 0, 1, 0, 1]], dtype=torch.bool)
    weight = torch.tensor([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    bias = torch.zeros(2)
    targets = torch.tensor([0, 1])
    logits, _, _ = submission.masked_sequence_classification_loss(hidden, mask, weight, bias, targets)
    expected_selected = torch.stack((hidden[0, 2], hidden[1, 4]))
    assert torch.equal(logits, expected_selected @ weight.t())


def test_extreme_logits_are_stable(submission):
    hidden = torch.tensor([[[10000.0, -10000.0]]])
    mask = torch.ones(1, 1, dtype=torch.bool)
    weight = torch.tensor([[1.0, 0.0], [0.9999, 0.0]])
    logits, loss, predictions = submission.masked_sequence_classification_loss(
        hidden, mask, weight, torch.zeros(2), torch.tensor([1])
    )
    assert torch.isfinite(logits).all() and torch.isfinite(loss)
    assert predictions.shape == (1,) and predictions.dtype == torch.long
    assert torch.allclose(loss, F.cross_entropy(logits, torch.tensor([1])), atol=1e-6)


def test_gradient_reaches_only_selected_hidden_rows_and_classifier(submission):
    hidden = torch.randn(2, 4, 3, dtype=torch.float64, requires_grad=True)
    weight = torch.randn(4, 3, dtype=torch.float64, requires_grad=True)
    bias = torch.randn(4, dtype=torch.float64, requires_grad=True)
    mask = torch.tensor([[1, 0, 1, 0], [0, 1, 0, 0]], dtype=torch.bool)
    _, loss, _ = submission.masked_sequence_classification_loss(
        hidden, mask, weight, bias, torch.tensor([2, 1])
    )
    loss.backward()
    assert hidden.grad is not None and weight.grad is not None and bias.grad is not None
    assert torch.count_nonzero(hidden.grad[0, [0, 1, 3]]) == 0
    assert torch.count_nonzero(hidden.grad[1, [0, 2, 3]]) == 0
    assert torch.count_nonzero(hidden.grad[0, 2]) > 0 and torch.count_nonzero(hidden.grad[1, 1]) > 0


def test_non_contiguous_hidden_dtype_and_cpu(submission):
    base = torch.randn(2, 3, 8, dtype=torch.float64)
    hidden = base[..., ::2]
    assert not hidden.is_contiguous()
    weight = torch.randn(3, 4, dtype=torch.float64)
    logits, loss, predictions = submission.masked_sequence_classification_loss(
        hidden, torch.ones(2, 3, dtype=torch.bool), weight,
        torch.zeros(3, dtype=torch.float64), torch.tensor([0, 2]),
    )
    assert logits.shape == (2, 3) and loss.shape == () and predictions.shape == (2,)
    assert logits.dtype == loss.dtype == torch.float64 and logits.device.type == "cpu"


@pytest.mark.parametrize(
    "hidden,mask,weight,bias,targets",
    [
        (torch.zeros(1, 2), torch.ones(1, 2, dtype=torch.bool), torch.zeros(2, 2), torch.zeros(2), torch.tensor([0])),
        (torch.zeros(1, 2, 3), torch.zeros(1, 2, dtype=torch.bool), torch.zeros(2, 3), torch.zeros(2), torch.tensor([0])),
        (torch.zeros(1, 2, 3), torch.ones(1, 2), torch.zeros(2, 3), torch.zeros(2), torch.tensor([0])),
        (torch.zeros(1, 2, 3), torch.ones(1, 2, dtype=torch.bool), torch.zeros(1, 3), torch.zeros(1), torch.tensor([0])),
        (torch.zeros(1, 2, 3), torch.ones(1, 2, dtype=torch.bool), torch.zeros(2, 3), torch.zeros(2), torch.tensor([2])),
    ],
)
def test_invalid_contract_raises_value_error(submission, hidden, mask, weight, bias, targets):
    with pytest.raises(ValueError):
        submission.masked_sequence_classification_loss(hidden, mask, weight, bias, targets)


def test_inputs_are_not_mutated(submission):
    hidden = torch.randn(2, 2, 3)
    mask = torch.tensor([[1, 0], [1, 1]], dtype=torch.bool)
    weight, bias, targets = torch.randn(2, 3), torch.randn(2), torch.tensor([0, 1])
    before = tuple(value.clone() for value in (hidden, mask, weight, bias, targets))
    submission.masked_sequence_classification_loss(hidden, mask, weight, bias, targets)
    assert all(torch.equal(value, original) for value, original in zip((hidden, mask, weight, bias, targets), before))
