import pytest

torch = pytest.importorskip("torch")


def _reference(packed, sequence_length):
    batch, heads, packed_width = packed.shape
    head_dim = packed_width // sequence_length
    return packed.reshape(batch, heads, sequence_length, head_dim).permute(0, 2, 1, 3).reshape(batch, sequence_length, heads * head_dim)


def test_unpacks_and_reorders_head_features(submission):
    packed = torch.arange(24).reshape(1, 2, 12)
    actual = submission.pack_head_features(packed, 3)
    assert actual.shape == (1, 3, 8)
    assert torch.equal(actual, _reference(packed, 3))


def test_supports_non_contiguous_packed_input(submission):
    base = torch.randn(2, 3, 16)
    packed = base[:, :, ::2]
    assert not packed.is_contiguous()
    actual = submission.pack_head_features(packed, 4)
    assert actual.is_contiguous()
    assert torch.allclose(actual, _reference(packed, 4))


def test_preserves_dtype_device_and_gradient(submission):
    packed = torch.randn(2, 2, 12, dtype=torch.float64, requires_grad=True)
    actual = submission.pack_head_features(packed, 3)
    assert actual.dtype == packed.dtype and actual.device == packed.device
    actual.sum().backward()
    assert torch.equal(packed.grad, torch.ones_like(packed))


@pytest.mark.parametrize(
    "packed,sequence_length",
    [
        (torch.zeros(2, 8), 2),
        (torch.zeros(1, 2, 7), 3),
        (torch.zeros(1, 2, 8), 0),
        (torch.zeros(1, 2, 8), True),
    ],
)
def test_rejects_invalid_contract(submission, packed, sequence_length):
    with pytest.raises(ValueError):
        submission.pack_head_features(packed, sequence_length)


def test_does_not_mutate_input(submission):
    packed = torch.randn(2, 3, 8)
    before = packed.clone()
    submission.pack_head_features(packed, 4)
    assert torch.equal(packed, before)
