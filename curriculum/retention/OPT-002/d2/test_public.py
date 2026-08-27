import pytest

torch = pytest.importorskip("torch")


def test_first_step_uses_gradient_as_velocity(submission):
    p, g = torch.tensor([1.0, -2.0]), torch.tensor([0.5, -1.0])
    updated, velocity = submission.functional_momentum(p, g, None, 0.2, 0.9)
    assert torch.equal(velocity, g)
    assert torch.allclose(updated, torch.tensor([0.9, -1.8]))


def test_later_step_uses_previous_velocity(submission):
    p, g, old = torch.tensor([1.0]), torch.tensor([2.0]), torch.tensor([4.0])
    updated, velocity = submission.functional_momentum(p, g, old, 0.1, 0.5)
    assert torch.equal(velocity, torch.tensor([4.0]))
    assert torch.equal(updated, torch.tensor([0.6]))


def test_inputs_are_not_mutated_or_aliased(submission):
    p, g, old = torch.tensor([1.0]), torch.tensor([0.5]), torch.tensor([0.25])
    before = p.clone(), g.clone(), old.clone()
    updated, velocity = submission.functional_momentum(p, g, old, 0.1, 0.9)
    assert all(torch.equal(x, y) for x, y in zip((p, g, old), before))
    assert updated.data_ptr() != p.data_ptr() and velocity.data_ptr() != old.data_ptr()


def test_outputs_are_detached_and_preserve_dtype_device(submission):
    p = torch.ones(2, dtype=torch.float64, requires_grad=True)
    g = torch.ones_like(p, requires_grad=True)
    updated, velocity = submission.functional_momentum(p, g, None, 0.01, 0.8)
    assert not updated.requires_grad and not velocity.requires_grad
    assert updated.dtype == p.dtype and updated.device == p.device


def test_multiple_functional_steps_match_torch_sgd(submission):
    actual, state = torch.tensor([1.0], dtype=torch.float64), None
    expected = torch.nn.Parameter(actual.clone())
    optimizer = torch.optim.SGD([expected], lr=0.03, momentum=0.7)
    for value in (0.2, -0.5, 0.1):
        gradient = torch.tensor([value], dtype=torch.float64)
        actual, state = submission.functional_momentum(actual, gradient, state, 0.03, 0.7)
        expected.grad = gradient.clone(); optimizer.step()
    assert torch.allclose(actual, expected.detach(), atol=1e-8)


@pytest.mark.parametrize("lr,momentum", [(0.0, 0.5), (0.1, -0.1), (0.1, 1.0), (0.1, True)])
def test_invalid_hyperparameters_raise(submission, lr, momentum):
    with pytest.raises(ValueError):
        submission.functional_momentum(torch.ones(1), torch.ones(1), None, lr, momentum)


def test_mismatched_velocity_raises(submission):
    with pytest.raises(ValueError):
        submission.functional_momentum(torch.ones(2), torch.ones(2), torch.ones(3), 0.1, 0.9)
