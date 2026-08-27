import pytest

torch = pytest.importorskip("torch")


def test_merges_heads_in_sequence_major_order(submission):
    head_states = torch.arange(24).reshape(1, 2, 3, 4)
    actual = submission.merge_heads(head_states)
    expected = head_states.permute(0, 2, 1, 3).reshape(1, 3, 8)
    assert actual.shape == (1, 3, 8)
    assert torch.equal(actual, expected)


def test_returns_contiguous_output_from_non_contiguous_input(submission):
    sequence_major = torch.randn(2, 4, 3, 5)
    head_states = sequence_major.permute(0, 2, 1, 3)
    assert not head_states.is_contiguous()
    actual = submission.merge_heads(head_states)
    expected = head_states.permute(0, 2, 1, 3).reshape(2, 4, 15)
    assert actual.is_contiguous()
    assert torch.equal(actual, expected)


def test_preserves_dtype_device_and_gradient(submission):
    head_states = torch.randn(2, 3, 4, 2, dtype=torch.float64, requires_grad=True)
    actual = submission.merge_heads(head_states)
    assert actual.dtype == head_states.dtype
    assert actual.device == head_states.device
    actual.square().sum().backward()
    assert torch.allclose(head_states.grad, 2 * head_states.detach())


@pytest.mark.parametrize("shape", [(2, 3, 4), (2, 3, 4, 5, 6)])
def test_rejects_non_rank_four_inputs(submission, shape):
    with pytest.raises(ValueError):
        submission.merge_heads(torch.zeros(shape))


def test_does_not_mutate_input(submission):
    head_states = torch.randn(2, 3, 4, 5)
    before = head_states.clone()
    submission.merge_heads(head_states)
    assert head_states.shape == before.shape
    assert torch.equal(head_states, before)
