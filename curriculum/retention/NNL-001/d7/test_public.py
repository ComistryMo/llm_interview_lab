import pytest

torch = pytest.importorskip("torch")


def test_constructor_registers_zero_parameters_with_expected_shapes(submission):
    layer = submission.LoadedLinear(3, 4, bias=True)
    assert tuple(layer.weight.shape) == (4, 3)
    assert tuple(layer.bias.shape) == (4,)
    assert dict(layer.named_parameters()).keys() == {"weight", "bias"}
    assert torch.count_nonzero(layer.weight) == 0 and torch.count_nonzero(layer.bias) == 0


def test_loading_and_forward_match_explicit_formula(submission):
    layer = submission.LoadedLinear(2, 3)
    weight = torch.tensor([[1.0, 2.0], [-1.0, 0.5], [3.0, -2.0]])
    bias = torch.tensor([0.25, -0.5, 1.0])
    layer.load_parameters(weight, bias)
    x = torch.tensor([[2.0, -1.0], [0.0, 3.0]])
    assert torch.allclose(layer(x), x @ weight.T + bias)


def test_loaded_values_are_copied_not_aliased(submission):
    layer = submission.LoadedLinear(2, 1)
    weight, bias = torch.tensor([[2.0, 3.0]]), torch.tensor([4.0])
    layer.load_parameters(weight, bias)
    weight.zero_(); bias.zero_()
    assert torch.equal(layer.weight, torch.tensor([[2.0, 3.0]]))
    assert torch.equal(layer.bias, torch.tensor([4.0]))


def test_bias_free_variant_rejects_a_bias_value(submission):
    layer = submission.LoadedLinear(2, 3, bias=False)
    assert layer.bias is None
    layer.load_parameters(torch.ones(3, 2))
    assert torch.equal(layer(torch.ones(1, 2)), torch.full((1, 3), 2.0))
    with pytest.raises(ValueError):
        layer.load_parameters(torch.ones(3, 2), torch.ones(3))


def test_gradients_reach_input_and_loaded_parameters(submission):
    layer = submission.LoadedLinear(2, 3).double()
    layer.load_parameters(torch.randn(3, 2, dtype=torch.float64), torch.randn(3, dtype=torch.float64))
    x = torch.randn(4, 2, dtype=torch.float64, requires_grad=True)
    layer(x).sum().backward()
    assert x.grad is not None and layer.weight.grad is not None and layer.bias.grad is not None


def test_invalid_load_is_atomic(submission):
    layer = submission.LoadedLinear(2, 2)
    layer.load_parameters(torch.eye(2), torch.tensor([1.0, 2.0]))
    before = (layer.weight.detach().clone(), layer.bias.detach().clone())
    with pytest.raises(ValueError):
        layer.load_parameters(torch.ones(3, 2), torch.ones(2))
    assert torch.equal(layer.weight, before[0]) and torch.equal(layer.bias, before[1])


@pytest.mark.parametrize("args", [(0, 2, True), (2, 0, True), (True, 2, True), (2, 3, 1)])
def test_invalid_constructor_raises_value_error(submission, args):
    with pytest.raises(ValueError):
        submission.LoadedLinear(*args)
