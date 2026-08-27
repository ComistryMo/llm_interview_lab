import pytest

torch = pytest.importorskip("torch")


def test_lookup_appends_the_embedding_dimension(submission):
    weight = torch.arange(24.0).reshape(8, 3)
    ids = torch.tensor([[2, 5], [1, 2]])
    output = submission.lookup_embeddings(weight, ids)
    assert output.shape == (2, 2, 3)
    assert torch.equal(output, weight[ids])


def test_padding_outputs_are_zero_even_when_weight_row_is_not(submission):
    weight = torch.arange(15.0).reshape(5, 3)
    output = submission.lookup_embeddings(weight, torch.tensor([0, 2, 0]), padding_idx=0)
    assert torch.equal(output[[0, 2]], torch.zeros(2, 3))
    assert torch.equal(output[1], weight[2])


def test_padding_and_repeated_id_gradients_are_correct(submission):
    weight = torch.randn(5, 2, dtype=torch.float64, requires_grad=True)
    output = submission.lookup_embeddings(weight, torch.tensor([1, 0, 1]), padding_idx=0)
    output.sum().backward()
    assert torch.equal(weight.grad[0], torch.zeros(2, dtype=torch.float64))
    assert torch.equal(weight.grad[1], torch.full((2,), 2.0, dtype=torch.float64))


def test_empty_ids_preserve_shape_dtype_and_device(submission):
    weight = torch.randn(4, 3, dtype=torch.float64)
    output = submission.lookup_embeddings(weight, torch.empty(2, 0, dtype=torch.long))
    assert output.shape == (2, 0, 3)
    assert output.dtype == weight.dtype and output.device == weight.device


def test_inputs_are_not_mutated(submission):
    weight = torch.randn(4, 2)
    ids = torch.tensor([1, 3, 1])
    before = weight.clone(), ids.clone()
    submission.lookup_embeddings(weight, ids)
    assert torch.equal(weight, before[0]) and torch.equal(ids, before[1])


@pytest.mark.parametrize(
    "weight,ids,padding_idx",
    [
        (torch.ones(4), torch.tensor([1]), None),
        (torch.ones(4, 2), torch.tensor([1.0]), None),
        (torch.ones(4, 2), torch.tensor([-1]), None),
        (torch.ones(4, 2), torch.tensor([4]), None),
        (torch.ones(4, 2), torch.tensor([1]), True),
        (torch.ones(4, 2), torch.tensor([1]), 4),
    ],
)
def test_invalid_contract_raises_value_error(submission, weight, ids, padding_idx):
    with pytest.raises(ValueError):
        submission.lookup_embeddings(weight, ids, padding_idx)
