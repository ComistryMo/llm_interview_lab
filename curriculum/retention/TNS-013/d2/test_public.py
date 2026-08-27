import pytest

torch = pytest.importorskip("torch")


def test_returns_scalar_mean_squared_error(submission):
    predictions = torch.tensor([[1.0, 3.0], [2.0, -1.0]], requires_grad=True)
    targets = torch.tensor([[0.0, 1.0], [4.0, -1.0]], requires_grad=True)
    actual = submission.detached_target_mse(predictions, targets)
    expected = (predictions - targets.detach()).square().mean()
    assert actual.shape == ()
    assert torch.equal(actual, expected)


def test_gradient_flows_only_through_predictions(submission):
    predictions = torch.tensor([1.0, -2.0, 3.0], dtype=torch.float64, requires_grad=True)
    targets = torch.tensor([0.5, 1.0, -1.0], dtype=torch.float64, requires_grad=True)
    loss = submission.detached_target_mse(predictions, targets)
    loss.backward()
    expected = 2 * (predictions.detach() - targets.detach()) / predictions.numel()
    assert torch.allclose(predictions.grad, expected)
    assert targets.grad is None


def test_supports_non_contiguous_tensors_and_preserves_dtype_device(submission):
    predictions = torch.randn(3, 4, dtype=torch.float64).transpose(0, 1).detach().requires_grad_()
    targets = torch.randn(3, 4, dtype=torch.float64).transpose(0, 1).detach().requires_grad_()
    assert not predictions.is_contiguous() and not targets.is_contiguous()
    actual = submission.detached_target_mse(predictions, targets)
    assert actual.dtype == predictions.dtype and actual.device == predictions.device
    assert torch.allclose(actual, (predictions - targets.detach()).square().mean())


@pytest.mark.parametrize(
    "predictions,targets",
    [
        (torch.zeros(2, 3), torch.zeros(2, 2)),
        (torch.zeros(2, 3), torch.zeros(2, 3, dtype=torch.float64)),
        (torch.zeros(2, 3), torch.zeros(2, 3, dtype=torch.long)),
        (torch.empty(0), torch.empty(0)),
    ],
)
def test_rejects_invalid_contract(submission, predictions, targets):
    with pytest.raises(ValueError):
        submission.detached_target_mse(predictions, targets)


def test_does_not_mutate_or_alias_inputs(submission):
    predictions = torch.randn(2, 3, requires_grad=True)
    targets = torch.randn(2, 3, requires_grad=True)
    before_predictions = predictions.detach().clone()
    before_targets = targets.detach().clone()
    loss = submission.detached_target_mse(predictions, targets)
    assert loss.data_ptr() not in {predictions.data_ptr(), targets.data_ptr()}
    assert torch.equal(predictions.detach(), before_predictions)
    assert torch.equal(targets.detach(), before_targets)
