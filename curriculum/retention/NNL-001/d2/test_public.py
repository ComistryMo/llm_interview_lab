import pytest

torch = pytest.importorskip("torch")


def test_projects_the_last_axis_with_io_weight_orientation(submission):
    x = torch.tensor([[[1.0, 2.0], [-1.0, 3.0]]])
    weight = torch.tensor([[2.0, -1.0, 0.5], [1.0, 4.0, -2.0]])
    bias = torch.tensor([0.5, -0.5, 1.0])
    actual = submission.affine_projection(x, weight, bias)
    assert actual.shape == (1, 2, 3)
    assert torch.allclose(actual, x @ weight + bias)


def test_bias_is_optional(submission):
    x = torch.tensor([[1.0, -2.0]], dtype=torch.float64)
    weight = torch.tensor([[3.0], [4.0]], dtype=torch.float64)
    assert torch.equal(submission.affine_projection(x, weight), x @ weight)


def test_non_contiguous_input_and_gradients_are_supported(submission):
    base = torch.randn(2, 3, 4, dtype=torch.float64, requires_grad=True)
    x = base.transpose(0, 1)
    weight = torch.randn(4, 5, dtype=torch.float64, requires_grad=True)
    bias = torch.randn(5, dtype=torch.float64, requires_grad=True)
    output = submission.affine_projection(x, weight, bias)
    output.square().sum().backward()
    assert not x.is_contiguous()
    assert base.grad is not None and weight.grad is not None and bias.grad is not None


def test_dtype_and_device_follow_inputs(submission):
    x = torch.ones(2, 3, dtype=torch.float64)
    weight = torch.ones(3, 4, dtype=torch.float64)
    output = submission.affine_projection(x, weight)
    assert output.dtype == torch.float64 and output.device == x.device


def test_inputs_are_not_mutated(submission):
    x = torch.randn(3, 2)
    weight = torch.randn(2, 4)
    bias = torch.randn(4)
    before = tuple(t.clone() for t in (x, weight, bias))
    submission.affine_projection(x, weight, bias)
    assert all(torch.equal(value, saved) for value, saved in zip((x, weight, bias), before))


@pytest.mark.parametrize(
    "x,weight,bias",
    [
        (torch.ones(2, 3), torch.ones(4, 2), None),
        (torch.ones(2, 3), torch.ones(3, 2), torch.ones(3)),
        (torch.ones(2, 3, dtype=torch.int64), torch.ones(3, 2), None),
        (torch.ones(2, 3), torch.ones(3, 2, dtype=torch.float64), None),
    ],
)
def test_invalid_shape_or_dtype_raises_value_error(submission, x, weight, bias):
    with pytest.raises(ValueError):
        submission.affine_projection(x, weight, bias)
