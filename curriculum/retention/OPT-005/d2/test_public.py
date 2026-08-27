import copy
import pytest
import torch


def manual(parameter, gradient, state, lr, b1, b2, eps, wd):
    step = 1 if state is None else state["step"] + 1
    m0 = torch.zeros_like(parameter) if state is None else state["exp_avg"]
    v0 = torch.zeros_like(parameter) if state is None else state["exp_avg_sq"]
    m = b1 * m0 + (1 - b1) * gradient
    v = b2 * v0 + (1 - b2) * gradient.square()
    updated = parameter * (1 - lr * wd) - lr * (m / (1 - b1 ** step)) / ((v / (1 - b2 ** step)).sqrt() + eps)
    return updated, {"step": step, "exp_avg": m, "exp_avg_sq": v}


def test_first_step_matches_closed_form(submission):
    p, g = torch.tensor([1.0, -2.0], dtype=torch.float64), torch.tensor([0.2, -0.3], dtype=torch.float64)
    actual_p, actual_s = submission.functional_adamw(p, g, None, 0.01)
    expected_p, expected_s = manual(p, g, None, 0.01, 0.9, 0.999, 1e-8, 0.01)
    assert torch.allclose(actual_p, expected_p) and actual_s["step"] == 1
    assert torch.allclose(actual_s["exp_avg"], expected_s["exp_avg"])


def test_multiple_steps_match_closed_form(submission):
    p, state = torch.tensor([1.0]), None
    for grad in (torch.tensor([0.2]), torch.tensor([-0.1]), torch.tensor([0.4])):
        expected_p, expected_state = manual(p, grad, state, 0.03, 0.8, 0.95, 1e-6, 0.1)
        p, state = submission.functional_adamw(p, grad, state, 0.03, 0.8, 0.95, 1e-6, 0.1)
        assert torch.allclose(p, expected_p, atol=1e-7)
        assert state["step"] == expected_state["step"]


def test_inputs_are_not_mutated(submission):
    p, g = torch.tensor([1.0]), torch.tensor([0.5])
    state = {"step": 1, "exp_avg": torch.tensor([0.1]), "exp_avg_sq": torch.tensor([0.2])}
    before = copy.deepcopy(state)
    submission.functional_adamw(p, g, state, 0.1)
    assert torch.equal(p, torch.tensor([1.0])) and torch.equal(g, torch.tensor([0.5]))
    assert state["step"] == before["step"] and torch.equal(state["exp_avg"], before["exp_avg"])


@pytest.mark.parametrize("lr,wd", [(0.0, 0.1), (-0.1, 0.1), (0.1, -0.1)])
def test_invalid_hyperparameters(submission, lr, wd):
    with pytest.raises(ValueError):
        submission.functional_adamw(torch.ones(1), torch.ones(1), None, lr, weight_decay=wd)


def test_dtype_and_device_are_preserved(submission):
    p = torch.ones(2, dtype=torch.float64)
    updated, state = submission.functional_adamw(p, torch.ones_like(p), None, 0.01)
    assert updated.dtype == p.dtype and updated.device == p.device
    assert state["exp_avg"].dtype == p.dtype
