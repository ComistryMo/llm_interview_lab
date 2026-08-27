import pytest

torch = pytest.importorskip("torch")


def test_marks_padding_keys_in_rank_four_layout(submission):
    lengths = torch.tensor([3, 1, 0])
    actual = submission.padding_key_mask(lengths, 4)
    expected = torch.tensor(
        [
            [[[False, False, False, True]]],
            [[[False, True, True, True]]],
            [[[True, True, True, True]]],
        ]
    )
    assert actual.shape == (3, 1, 1, 4)
    assert actual.dtype == torch.bool
    assert torch.equal(actual, expected)


def test_supports_exact_maximum_length(submission):
    lengths = torch.tensor([2, 4])
    actual = submission.padding_key_mask(lengths, 4)
    assert torch.equal(actual[0, 0, 0], torch.tensor([False, False, True, True]))
    assert not actual[1].any()


def test_supports_empty_batch_with_explicit_width(submission):
    actual = submission.padding_key_mask(torch.empty(0, dtype=torch.long), 5)
    assert actual.shape == (0, 1, 1, 5)
    assert actual.dtype == torch.bool


def test_preserves_device_and_does_not_mutate_lengths(submission):
    lengths = torch.tensor([1, 3])
    before = lengths.clone()
    actual = submission.padding_key_mask(lengths, 3)
    assert actual.device == lengths.device
    assert torch.equal(lengths, before)


@pytest.mark.parametrize(
    "lengths,max_length",
    [
        (torch.tensor([[1, 2]]), 2),
        (torch.tensor([1.0, 2.0]), 2),
        (torch.tensor([-1, 2]), 2),
        (torch.tensor([3]), 2),
        (torch.tensor([1]), -1),
        (torch.tensor([1]), True),
    ],
)
def test_rejects_invalid_contract(submission, lengths, max_length):
    with pytest.raises(ValueError):
        submission.padding_key_mask(lengths, max_length)
