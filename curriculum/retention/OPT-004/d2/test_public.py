import copy
import pytest

torch = pytest.importorskip("torch")


def test_first_step_matches_closed_form(submission):
    p = torch.tensor([1.0, -2.0], dtype=torch.float64)
    g = torch.tensor([2.0, -4.0], dtype=torch.float64)
    updated, state = submission.functional_adam(p, g, None, 0.1)
    assert torch.allclose(updated, torch.tensor([0.9, -1.9], dtype=torch.float64), atol=1e-8)
    assert state["step"] == 1
    assert torch.allclose(state["exp_avg"], torch.tensor([0.2, -0.4], dtype=torch.float64))


def test_multiple_steps_match_torch_adam(submission):
    actual, state = torch.tensor([1.0], dtype=torch.float64), None
    expected = torch.nn.Parameter(actual.clone()); optimizer = torch.optim.Adam([expected], lr=0.02, betas=(0.7, 0.95), eps=1e-7)
    for value in (0.3, -0.2, 0.8):
        gradient = torch.tensor([value], dtype=torch.float64)
        actual, state = submission.functional_adam(actual, gradient, state, 0.02, 0.7, 0.95, 1e-7)
        expected.grad = gradient.clone(); optimizer.step()
    assert torch.allclose(actual, expected.detach(), atol=1e-8) and state["step"] == 3


def test_inputs_and_caller_state_are_not_mutated(submission):
    p, g = torch.tensor([1.0]), torch.tensor([0.5])
    state = {"step": 2, "exp_avg": torch.tensor([0.1]), "exp_avg_sq": torch.tensor([0.2])}
    before = p.clone(), g.clone(), copy.deepcopy(state)
    submission.functional_adam(p, g, state, 0.01)
    assert torch.equal(p, before[0]) and torch.equal(g, before[1])
    assert state["step"] == before[2]["step"]
    assert torch.equal(state["exp_avg"], before[2]["exp_avg"])


def test_outputs_are_detached_and_preserve_dtype_device(submission):
    p = torch.ones(2, dtype=torch.float64, requires_grad=True)
    g = torch.ones_like(p, requires_grad=True)
    updated, state = submission.functional_adam(p, g, None, 0.01)
    assert not updated.requires_grad and not state["exp_avg"].requires_grad
    assert updated.dtype == p.dtype and updated.device == p.device


@pytest.mark.parametrize("lr,beta1,beta2,eps", [(0.0, 0.9, 0.999, 1e-8), (0.1, 1.0, 0.999, 1e-8), (0.1, 0.9, 1.0, 1e-8), (0.1, 0.9, 0.999, 0.0)])
def test_invalid_hyperparameters_raise(submission, lr, beta1, beta2, eps):
    with pytest.raises(ValueError):
        submission.functional_adam(torch.ones(1), torch.ones(1), None, lr, beta1, beta2, eps)


def test_invalid_state_shape_raises(submission):
    state = {"step": 1, "exp_avg": torch.zeros(2), "exp_avg_sq": torch.zeros(2)}
    with pytest.raises(ValueError):
        submission.functional_adam(torch.ones(1), torch.ones(1), state, 0.1)
