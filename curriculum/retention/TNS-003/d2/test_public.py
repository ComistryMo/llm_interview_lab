import pytest

torch = pytest.importorskip("torch")


def test_applies_hidden_wise_affine_transform(submission):
    x = torch.arange(24.0).reshape(2, 3, 4)
    scale = torch.tensor([1.0, -1.0, 0.5, 2.0])
    shift = torch.tensor([3.0, 4.0, 5.0, 6.0])
    actual = submission.broadcast_affine(x, scale, shift)
    assert actual.shape == x.shape
    assert torch.equal(actual, x * scale + shift)


def test_supports_non_contiguous_input(submission):
    base = torch.randn(2, 5, 3)
    x = base.transpose(1, 2)
    assert not x.is_contiguous()
    scale = torch.randn(5)
    shift = torch.randn(5)
    assert torch.allclose(submission.broadcast_affine(x, scale, shift), x * scale + shift)


def test_gradients_reduce_across_broadcast_dimensions(submission):
    x = torch.randn(2, 3, 4, dtype=torch.float64, requires_grad=True)
    scale = torch.randn(4, dtype=torch.float64, requires_grad=True)
    shift = torch.randn(4, dtype=torch.float64, requires_grad=True)
    submission.broadcast_affine(x, scale, shift).sum().backward()
    assert torch.allclose(x.grad, scale.detach().expand_as(x))
    assert torch.allclose(scale.grad, x.detach().sum(dim=(0, 1)))
    assert torch.equal(shift.grad, torch.full_like(shift, 6))


@pytest.mark.parametrize(
    "x,scale,shift",
    [
        (torch.zeros(2, 3), torch.zeros(3), torch.zeros(3)),
        (torch.zeros(2, 3, 4), torch.zeros(1, 4), torch.zeros(4)),
        (torch.zeros(2, 3, 4), torch.zeros(5), torch.zeros(4)),
        (torch.zeros(2, 3, 4), torch.zeros(4), torch.zeros(5)),
        (torch.zeros(2, 3, 4), torch.zeros(4, dtype=torch.float64), torch.zeros(4)),
    ],
)
def test_rejects_invalid_shapes_and_dtypes(submission, x, scale, shift):
    with pytest.raises(ValueError):
        submission.broadcast_affine(x, scale, shift)


def test_does_not_mutate_any_input(submission):
    x = torch.randn(2, 3, 4)
    scale = torch.randn(4)
    shift = torch.randn(4)
    snapshots = (x.clone(), scale.clone(), shift.clone())
    submission.broadcast_affine(x, scale, shift)
    assert torch.equal(x, snapshots[0])
    assert torch.equal(scale, snapshots[1])
    assert torch.equal(shift, snapshots[2])
