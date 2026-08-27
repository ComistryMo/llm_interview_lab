import pytest

torch = pytest.importorskip("torch")


def test_matches_one_step_closed_form(submission):
    parameter = torch.tensor([1.0, -2.0], dtype=torch.float64)
    gradient = torch.tensor([0.5, -1.5], dtype=torch.float64)
    assert torch.allclose(submission.functional_sgd(parameter, gradient, 0.2), parameter - 0.2 * gradient)


def test_inputs_are_not_mutated(submission):
    parameter, gradient = torch.randn(4), torch.randn(4)
    before = parameter.clone(), gradient.clone()
    submission.functional_sgd(parameter, gradient, 0.1)
    assert torch.equal(parameter, before[0]) and torch.equal(gradient, before[1])


def test_result_is_detached_from_autograd(submission):
    parameter = torch.tensor([1.0], requires_grad=True)
    gradient = torch.tensor([2.0], requires_grad=True)
    result = submission.functional_sgd(parameter, gradient, 0.1)
    assert not result.requires_grad and result.grad_fn is None


def test_dtype_device_and_non_contiguous_shape_are_preserved(submission):
    parameter = torch.randn(3, 4, dtype=torch.float64).T
    gradient = torch.randn(3, 4, dtype=torch.float64).T
    result = submission.functional_sgd(parameter, gradient, 0.01)
    assert not parameter.is_contiguous()
    assert result.shape == parameter.shape and result.dtype == parameter.dtype
    assert result.device == parameter.device


@pytest.mark.parametrize("lr", [0.0, -0.1, float("inf"), float("nan"), True])
def test_invalid_learning_rate_raises(submission, lr):
    with pytest.raises(ValueError):
        submission.functional_sgd(torch.ones(1), torch.ones(1), lr)


@pytest.mark.parametrize(
    "parameter,gradient",
    [
        (torch.ones(2), torch.ones(3)),
        (torch.ones(2), torch.ones(2, dtype=torch.float64)),
        (torch.ones(2, dtype=torch.int64), torch.ones(2, dtype=torch.int64)),
    ],
)
def test_invalid_tensor_contract_raises(submission, parameter, gradient):
    with pytest.raises(ValueError):
        submission.functional_sgd(parameter, gradient, 0.1)
