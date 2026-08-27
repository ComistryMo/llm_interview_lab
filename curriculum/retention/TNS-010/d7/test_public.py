import pytest

torch = pytest.importorskip("torch")


def test_combines_causal_and_length_constraints(submission):
    lengths = torch.tensor([3, 1])
    actual = submission.causal_sequence_mask(lengths, 4)
    expected = torch.tensor(
        [
            [[1, 0, 0, 0], [1, 1, 0, 0], [1, 1, 1, 0], [0, 0, 0, 0]],
            [[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
        ],
        dtype=torch.bool,
    )
    assert actual.shape == (2, 4, 4)
    assert actual.dtype == torch.bool
    assert torch.equal(actual, expected)


def test_full_length_is_lower_triangular(submission):
    actual = submission.causal_sequence_mask(torch.tensor([5]), 5)
    assert torch.equal(actual[0], torch.ones(5, 5, dtype=torch.bool).tril())


def test_zero_length_has_no_allowed_attention(submission):
    actual = submission.causal_sequence_mask(torch.tensor([0]), 3)
    assert not actual.any()


def test_empty_batch_preserves_requested_shape(submission):
    actual = submission.causal_sequence_mask(torch.empty(0, dtype=torch.long), 3)
    assert actual.shape == (0, 3, 3)
    assert actual.dtype == torch.bool


def test_preserves_device_and_input(submission):
    lengths = torch.tensor([2, 4])
    before = lengths.clone()
    actual = submission.causal_sequence_mask(lengths, 4)
    assert actual.device == lengths.device
    assert torch.equal(lengths, before)


@pytest.mark.parametrize(
    "lengths,max_length",
    [
        (torch.tensor([[1]]), 2),
        (torch.tensor([1.0]), 2),
        (torch.tensor([-1]), 2),
        (torch.tensor([3]), 2),
        (torch.tensor([1]), -1),
        (torch.tensor([1]), True),
    ],
)
def test_rejects_invalid_contract(submission, lengths, max_length):
    with pytest.raises(ValueError):
        submission.causal_sequence_mask(lengths, max_length)
