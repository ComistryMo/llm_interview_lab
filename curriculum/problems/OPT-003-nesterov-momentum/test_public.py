import pytest

torch = pytest.importorskip("torch")


def test_first_step_closed_form(submission):
    p = torch.tensor([1., -2.], dtype=torch.float64)
    g = torch.tensor([.5, -1.], dtype=torch.float64)
    out, velocity = submission.nesterov_step(p, g, None, .1, .9)
    torch.testing.assert_close(out, torch.tensor([.905, -1.81], dtype=p.dtype))
    torch.testing.assert_close(velocity, g)


def test_two_steps_match_optimizer(submission):
    actual = torch.tensor([1., -2.], dtype=torch.float64)
    expected = torch.nn.Parameter(actual.clone())
    optimizer = torch.optim.SGD([expected], lr=.07, momentum=.8, nesterov=True)
    velocity = None
    for grad in (torch.tensor([.3, .5]), torch.tensor([-.4, .2]), torch.zeros(2)):
        grad = grad.to(actual)
        expected.grad = grad.clone()
        optimizer.step()
        actual, velocity = submission.nesterov_step(actual, grad, velocity, .07, .8)
        torch.testing.assert_close(actual, expected)


def test_noncontiguous_and_dtype(submission):
    p = torch.arange(12., dtype=torch.float32).reshape(3, 4).T
    g = torch.ones_like(p)
    out, v = submission.nesterov_step(p, g, None, .1, .5)
    torch.testing.assert_close(out, p - .15)
    assert out.dtype == p.dtype and out.device == p.device and v.shape == p.shape


def test_inputs_and_returned_state_are_independent(submission):
    p = torch.tensor([1., 2.], requires_grad=True)
    g = torch.tensor([.1, .2], requires_grad=True)
    v = torch.tensor([.3, .4], requires_grad=True)
    saved = [t.detach().clone() for t in (p, g, v)]
    out, next_v = submission.nesterov_step(p, g, v, .1, .9)
    assert not out.requires_grad and not next_v.requires_grad
    assert p.grad is g.grad is v.grad is None
    out.add_(10)
    next_v.add_(20)
    for actual, before in zip((p, g, v), saved):
        torch.testing.assert_close(actual, before)


@pytest.mark.parametrize("lr,momentum", [(0., .9), (.1, 0.), (.1, 1.), (float("nan"), .9), (True, .9)])
def test_invalid_hyperparameters(submission, lr, momentum):
    with pytest.raises(ValueError):
        submission.nesterov_step(torch.ones(2), torch.ones(2), None, lr, momentum)


@pytest.mark.parametrize("gradient,velocity", [
    (torch.ones(3), None), (torch.ones(2, dtype=torch.float64), None),
    (torch.ones(2), torch.ones(3)), (torch.tensor([float("nan"), 1.]), None)
])
def test_invalid_tensors(submission, gradient, velocity):
    p = torch.ones(2)
    with pytest.raises(ValueError):
        submission.nesterov_step(p, gradient, velocity, .1, .9)
    torch.testing.assert_close(p, torch.ones(2))
