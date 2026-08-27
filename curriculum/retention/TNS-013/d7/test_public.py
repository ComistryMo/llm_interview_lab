import pytest

torch = pytest.importorskip("torch")


def test_computes_functional_ema_values(submission):
    current = torch.tensor([2.0, 6.0], requires_grad=True)
    previous = torch.tensor([10.0, -2.0], requires_grad=True)
    actual = submission.ema_snapshot(current, previous, 0.25)
    expected = 0.25 * previous.detach() + 0.75 * current.detach()
    assert torch.allclose(actual, expected)


@pytest.mark.parametrize("decay,expected_source", [(0.0, "current"), (1.0, "previous")])
def test_supports_decay_boundaries_without_aliasing(submission, decay, expected_source):
    current = torch.tensor([1.0, 2.0])
    previous = torch.tensor([3.0, 4.0])
    actual = submission.ema_snapshot(current, previous, decay)
    expected = current if expected_source == "current" else previous
    assert torch.equal(actual, expected)
    assert actual.data_ptr() not in {current.data_ptr(), previous.data_ptr()}


def test_result_has_no_autograd_history(submission):
    current = torch.randn(2, 3, requires_grad=True)
    previous = torch.randn(2, 3, requires_grad=True)
    actual = submission.ema_snapshot(current, previous, 0.9)
    assert not actual.requires_grad
    assert actual.grad_fn is None


def test_supports_non_contiguous_inputs_and_preserves_dtype_device(submission):
    current = torch.randn(3, 4, dtype=torch.float64).transpose(0, 1)
    previous = torch.randn(3, 4, dtype=torch.float64).transpose(0, 1)
    actual = submission.ema_snapshot(current, previous, 0.5)
    assert actual.dtype == current.dtype and actual.device == current.device
    assert torch.allclose(actual, 0.5 * previous + 0.5 * current)


@pytest.mark.parametrize(
    "current,previous,decay",
    [
        (torch.zeros(2, 3), torch.zeros(2, 2), 0.5),
        (torch.zeros(2, 3), torch.zeros(2, 3, dtype=torch.float64), 0.5),
        (torch.zeros(2, 3, dtype=torch.long), torch.zeros(2, 3, dtype=torch.long), 0.5),
        (torch.zeros(2, 3), torch.zeros(2, 3), True),
        (torch.zeros(2, 3), torch.zeros(2, 3), -0.1),
        (torch.zeros(2, 3), torch.zeros(2, 3), 1.1),
    ],
)
def test_rejects_invalid_contract(submission, current, previous, decay):
    with pytest.raises(ValueError):
        submission.ema_snapshot(current, previous, decay)


def test_does_not_mutate_inputs_or_share_storage(submission):
    current = torch.randn(2, 3)
    previous = torch.randn(2, 3)
    before_current, before_previous = current.clone(), previous.clone()
    actual = submission.ema_snapshot(current, previous, 0.8)
    actual.add_(10)
    assert torch.equal(current, before_current)
    assert torch.equal(previous, before_previous)
