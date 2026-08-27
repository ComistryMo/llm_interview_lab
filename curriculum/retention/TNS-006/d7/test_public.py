import pytest

torch = pytest.importorskip("torch")


def test_gathers_token_values_and_zeros_invalid_positions(submission):
    values = torch.tensor([[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]])
    token_ids = torch.tensor([[2, 0, 1]])
    valid_mask = torch.tensor([[True, False, True]])
    actual = submission.gather_masked_token_values(values, token_ids, valid_mask)
    assert actual.shape == (1, 3)
    assert torch.equal(actual, torch.tensor([[3.0, 0.0, 8.0]]))


def test_matches_gather_reference_for_batched_inputs(submission):
    values = torch.randn(2, 4, 5, dtype=torch.float64)
    token_ids = torch.tensor([[0, 4, 2, 1], [3, 2, 0, 4]])
    valid_mask = torch.tensor([[1, 1, 0, 1], [0, 1, 1, 1]], dtype=torch.bool)
    gathered = torch.gather(values, -1, token_ids.unsqueeze(-1)).squeeze(-1)
    expected = gathered.masked_fill(~valid_mask, 0)
    actual = submission.gather_masked_token_values(values, token_ids, valid_mask)
    assert torch.equal(actual, expected)


def test_gradient_reaches_only_valid_selected_values(submission):
    values = torch.randn(1, 3, 4, dtype=torch.float64, requires_grad=True)
    token_ids = torch.tensor([[1, 2, 1]])
    valid_mask = torch.tensor([[True, False, True]])
    submission.gather_masked_token_values(values, token_ids, valid_mask).sum().backward()
    expected = torch.zeros_like(values)
    expected[0, 0, 1] = 1
    expected[0, 2, 1] = 1
    assert torch.equal(values.grad, expected)


def test_supports_non_contiguous_values(submission):
    base = torch.randn(2, 6, 3)
    values = base.transpose(1, 2)
    assert not values.is_contiguous()
    token_ids = torch.tensor([[5, 0, 2], [1, 4, 3]])
    mask = torch.tensor([[1, 1, 0], [1, 0, 1]], dtype=torch.bool)
    expected = torch.gather(values, -1, token_ids.unsqueeze(-1)).squeeze(-1).masked_fill(~mask, 0)
    assert torch.allclose(submission.gather_masked_token_values(values, token_ids, mask), expected)


@pytest.mark.parametrize(
    "values,ids,mask",
    [
        (torch.zeros(2, 3), torch.zeros(2, dtype=torch.long), torch.ones(2, dtype=torch.bool)),
        (torch.zeros(2, 3, 4), torch.zeros(2, 2, dtype=torch.long), torch.ones(2, 3, dtype=torch.bool)),
        (torch.zeros(2, 3, 4), torch.zeros(2, 3), torch.ones(2, 3, dtype=torch.bool)),
        (torch.zeros(2, 3, 4), torch.zeros(2, 3, dtype=torch.long), torch.ones(2, 3)),
        (torch.zeros(2, 3, 4), torch.full((2, 3), 4, dtype=torch.long), torch.ones(2, 3, dtype=torch.bool)),
    ],
)
def test_rejects_invalid_contract(submission, values, ids, mask):
    with pytest.raises(ValueError):
        submission.gather_masked_token_values(values, ids, mask)


def test_preserves_dtype_device_and_inputs(submission):
    values = torch.randn(1, 2, 3, dtype=torch.float64)
    ids = torch.tensor([[0, 2]])
    mask = torch.tensor([[True, False]])
    snapshots = (values.clone(), ids.clone(), mask.clone())
    actual = submission.gather_masked_token_values(values, ids, mask)
    assert actual.dtype == values.dtype and actual.device == values.device
    assert torch.equal(values, snapshots[0])
    assert torch.equal(ids, snapshots[1])
    assert torch.equal(mask, snapshots[2])
