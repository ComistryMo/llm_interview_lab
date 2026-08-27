import pytest

torch = pytest.importorskip("torch")


def test_masked_mean_matches_hand_computed_rows(submission):
    weight = torch.tensor([[0.0, 0.0], [2.0, 4.0], [6.0, 8.0], [10.0, 12.0]])
    ids = torch.tensor([[1, 2, 0], [3, 1, 2]])
    mask = torch.tensor([[True, True, False], [True, False, False]])
    expected = torch.tensor([[4.0, 6.0], [10.0, 12.0]])
    assert torch.equal(submission.masked_mean_embedding(weight, ids, mask), expected)


def test_different_valid_lengths_do_not_change_output_shape(submission):
    weight = torch.randn(9, 5)
    ids = torch.tensor([[1, 2, 3, 4], [5, 6, 0, 0], [7, 0, 0, 0]])
    mask = torch.tensor([[1, 1, 1, 1], [1, 1, 0, 0], [1, 0, 0, 0]], dtype=torch.bool)
    assert submission.masked_mean_embedding(weight, ids, mask).shape == (3, 5)


def test_only_valid_rows_receive_gradient(submission):
    weight = torch.randn(6, 3, dtype=torch.float64, requires_grad=True)
    ids = torch.tensor([[1, 2, 3], [4, 5, 0]])
    mask = torch.tensor([[True, False, True], [True, False, False]])
    submission.masked_mean_embedding(weight, ids, mask).sum().backward()
    assert torch.count_nonzero(weight.grad[2]) == 0
    assert torch.count_nonzero(weight.grad[5]) == 0
    assert torch.count_nonzero(weight.grad[1]) == 3


def test_dtype_device_and_non_contiguous_inputs_are_supported(submission):
    weight = torch.randn(7, 4, dtype=torch.float64)
    ids = torch.tensor([[1, 2], [3, 4], [5, 6]]).T
    mask = torch.ones_like(ids, dtype=torch.bool)
    assert not ids.is_contiguous()
    output = submission.masked_mean_embedding(weight, ids, mask)
    assert output.dtype == weight.dtype and output.device == weight.device


def test_inputs_are_not_mutated(submission):
    weight = torch.randn(5, 2)
    ids = torch.tensor([[1, 2], [3, 4]])
    mask = torch.tensor([[True, False], [True, True]])
    before = weight.clone(), ids.clone(), mask.clone()
    submission.masked_mean_embedding(weight, ids, mask)
    assert all(torch.equal(x, y) for x, y in zip((weight, ids, mask), before))


@pytest.mark.parametrize(
    "ids,mask",
    [
        (torch.tensor([[1, 2]]), torch.tensor([[True, False], [True, False]])),
        (torch.tensor([[1, 2]]), torch.tensor([[1, 0]])),
        (torch.tensor([[1, 2]]), torch.tensor([[False, False]])),
        (torch.tensor([[1, 5]]), torch.tensor([[True, False]])),
    ],
)
def test_invalid_mask_or_ids_raise_value_error(submission, ids, mask):
    with pytest.raises(ValueError):
        submission.masked_mean_embedding(torch.ones(5, 3), ids, mask)
