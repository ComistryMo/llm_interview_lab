import pytest

torch = pytest.importorskip("torch")


def test_selects_multiple_rows_per_batch(submission):
    values = torch.arange(30.0).reshape(2, 5, 3)
    indices = torch.tensor([[4, 0], [1, 3]])
    actual = submission.batched_select_rows(values, indices)
    expected = torch.stack((values[0, indices[0]], values[1, indices[1]]))
    assert actual.shape == (2, 2, 3)
    assert torch.equal(actual, expected)


def test_supports_non_contiguous_values(submission):
    base = torch.randn(2, 4, 5)
    values = base.transpose(1, 2)
    assert not values.is_contiguous()
    indices = torch.tensor([[0, 3, 4], [4, 2, 1]])
    expected = torch.gather(values, 1, indices.unsqueeze(-1).expand(-1, -1, values.shape[-1]))
    assert torch.allclose(submission.batched_select_rows(values, indices), expected)


def test_duplicate_rows_accumulate_gradient(submission):
    values = torch.randn(1, 4, 2, dtype=torch.float64, requires_grad=True)
    indices = torch.tensor([[2, 2, 0]])
    submission.batched_select_rows(values, indices).sum().backward()
    expected = torch.zeros_like(values)
    expected[0, 0] = 1
    expected[0, 2] = 2
    assert torch.equal(values.grad, expected)


@pytest.mark.parametrize(
    "values,indices",
    [
        (torch.zeros(2, 3), torch.tensor([[0], [1]])),
        (torch.zeros(2, 3, 4), torch.tensor([0, 1])),
        (torch.zeros(2, 3, 4), torch.tensor([[0], [1], [2]])),
        (torch.zeros(2, 3, 4), torch.tensor([[0.0], [1.0]])),
        (torch.zeros(2, 3, 4), torch.tensor([[3], [0]])),
        (torch.zeros(2, 3, 4), torch.tensor([[-1], [0]])),
    ],
)
def test_rejects_invalid_contract(submission, values, indices):
    with pytest.raises(ValueError):
        submission.batched_select_rows(values, indices)


def test_preserves_dtype_device_and_inputs(submission):
    values = torch.randn(2, 3, 4, dtype=torch.float64)
    indices = torch.tensor([[0, 2], [1, 1]])
    before_values, before_indices = values.clone(), indices.clone()
    actual = submission.batched_select_rows(values, indices)
    assert actual.dtype == values.dtype and actual.device == values.device
    assert torch.equal(values, before_values)
    assert torch.equal(indices, before_indices)
