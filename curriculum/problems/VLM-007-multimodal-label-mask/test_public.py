import pytest

torch = pytest.importorskip("torch")
F = torch.nn.functional


def _reference(logits, ids, attn, assistant, image, ignore_index):
    labels = ids.clone()
    valid = attn & assistant & ~image
    labels[~valid] = ignore_index
    shifted_labels = labels[:, 1:]
    shifted_logits = logits[:, :-1, :]
    flat_valid = shifted_labels != ignore_index
    if not flat_valid.any(dim=1).all():
        raise ValueError
    loss = F.cross_entropy(
        shifted_logits.reshape(-1, shifted_logits.shape[-1]),
        shifted_labels.reshape(-1),
        ignore_index=ignore_index,
        reduction="mean",
    )
    return loss, labels


def _batch(dtype=torch.float64, device="cpu"):
    logits = torch.tensor(
        [
            [[0.0, 2.0, -1.0], [1.0, 0.0, 3.0], [2.0, 1.0, 0.0], [0.0, 1.0, 2.0], [2.0, 0.0, 1.0]],
            [[1.0, 0.0, 2.0], [2.0, 1.0, 0.0], [0.0, 3.0, 1.0], [1.0, 2.0, 0.0], [0.0, 1.0, 3.0]],
        ],
        dtype=dtype,
        device=device,
    )
    ids = torch.tensor([[0, 1, 2, 1, 99], [1, 2, 0, 2, 99]], dtype=torch.long, device=device)
    attn = torch.tensor([[1, 1, 1, 1, 0], [1, 1, 1, 1, 0]], dtype=torch.bool, device=device)
    assistant = torch.tensor([[0, 0, 1, 1, 0], [0, 1, 0, 1, 0]], dtype=torch.bool, device=device)
    image = torch.tensor([[0, 0, 0, 1, 0], [0, 1, 0, 0, 0]], dtype=torch.bool, device=device)
    return logits, ids, attn, assistant, image


def test_matches_reference_and_returns_fresh_labels(submission):
    values = _batch()
    before = [x.clone() for x in values]
    loss, labels = submission.multimodal_sft_loss(*values)
    expected_loss, expected_labels = _reference(*values, -100)
    assert torch.allclose(loss, expected_loss, atol=1e-12, rtol=1e-12)
    assert torch.equal(labels, expected_labels)
    assert labels.shape == values[1].shape and labels.dtype == values[1].dtype
    assert labels.data_ptr() != values[1].data_ptr()
    assert all(torch.equal(now, old) for now, old in zip(values, before))


def test_image_mask_wins_and_padding_is_ignored(submission):
    logits, ids, attn, assistant, image = _batch()
    _, labels = submission.multimodal_sft_loss(logits, ids, attn, assistant, image)
    assert labels[0].tolist() == [-100, -100, 2, -100, -100]
    assert labels[1].tolist() == [-100, -100, -100, 2, -100]


def test_causal_shift_uses_target_positions_and_gradient_only_logits(submission):
    logits, ids, attn, assistant, image = _batch()
    logits = logits.clone().requires_grad_()
    loss, labels = submission.multimodal_sft_loss(logits, ids, attn, assistant, image)
    loss.backward()
    assert loss.shape == () and loss.dtype == logits.dtype and loss.device == logits.device
    assert logits.grad is not None
    # The only valid targets are at input positions 2 and 3; their predictors
    # are positions 1 and 2 after the causal shift.
    assert torch.count_nonzero(logits.grad[:, [0, 3, 4], :]) == 0
    assert torch.count_nonzero(logits.grad[:, [1, 2], :]) > 0
    assert not labels.requires_grad


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_dtype_and_device_are_preserved(submission, dtype):
    values = _batch(dtype=dtype)
    loss, labels = submission.multimodal_sft_loss(*values)
    assert loss.dtype == dtype and loss.device == values[0].device
    assert labels.dtype == values[1].dtype and labels.device == values[1].device


def test_each_row_needs_a_shifted_target(submission):
    logits, ids, attn, assistant, image = _batch()
    assistant[1].zero_()
    with pytest.raises(ValueError):
        submission.multimodal_sft_loss(logits, ids, attn, assistant, image)


@pytest.mark.parametrize(
    "mutator",
    [
        lambda x: (x[0][:, :-1, :], *x[1:]),
        lambda x: (x[0], x[1][:, :-1], x[2], x[3], x[4]),
        lambda x: (x[0], x[1], x[2].to(torch.int64), x[3], x[4]),
        lambda x: (x[0], x[1], x[2], x[3], x[4].to("meta")),
    ],
)
def test_invalid_shapes_dtypes_or_devices_raise(submission, mutator):
    values = _batch()
    with pytest.raises((ValueError, RuntimeError)):
        submission.multimodal_sft_loss(*mutator(values))


def test_invalid_ids_logits_and_ignore_index_raise(submission):
    values = list(_batch())
    values[1] = values[1].clone()
    values[1][0, 2] = 3  # valid target, outside vocab
    with pytest.raises(ValueError):
        submission.multimodal_sft_loss(*values)

    values = list(_batch())
    values[0] = torch.full_like(values[0], float("inf"))
    with pytest.raises(ValueError):
        submission.multimodal_sft_loss(*values)

    values = list(_batch())
    with pytest.raises(ValueError):
        submission.multimodal_sft_loss(*values, ignore_index=True)
