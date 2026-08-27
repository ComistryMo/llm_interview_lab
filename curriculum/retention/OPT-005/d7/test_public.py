import copy
import torch


def group(name, parameter, lr, weight_decay):
    return {"params": [(name, parameter)], "lr": lr, "betas": (0.9, 0.999), "eps": 1e-8, "weight_decay": weight_decay}


def torch_reference(value, grad, lr, wd, steps=1):
    p = torch.nn.Parameter(value.clone())
    opt = torch.optim.AdamW([p], lr=lr, weight_decay=wd)
    for _ in range(steps):
        p.grad = grad.clone()
        opt.step()
    return p.detach()


def test_parameter_groups_match_torch_first_step(submission):
    p1, p2 = torch.tensor([1.0]), torch.tensor([2.0])
    p1.grad, p2.grad = torch.tensor([0.2]), torch.tensor([-0.3])
    states = submission.grouped_adamw_step([group("a", p1, 0.01, 0.1), group("b", p2, 0.03, 0.0)], {})
    assert torch.allclose(p1, torch_reference(torch.tensor([1.0]), torch.tensor([0.2]), 0.01, 0.1))
    assert torch.allclose(p2, torch_reference(torch.tensor([2.0]), torch.tensor([-0.3]), 0.03, 0.0))
    assert set(states) == {"a", "b"}


def test_none_gradient_is_skipped(submission):
    p = torch.tensor([1.0])
    states = submission.grouped_adamw_step([group("a", p, 0.1, 0.2)], {})
    assert torch.equal(p, torch.tensor([1.0])) and states == {}


def test_multi_step_and_resume_are_deterministic(submission):
    p = torch.tensor([1.0])
    p.grad = torch.tensor([0.25])
    first = submission.grouped_adamw_step([group("a", p, 0.02, 0.1)], {})
    saved = copy.deepcopy(first)
    p.grad = torch.tensor([0.25])
    second = submission.grouped_adamw_step([group("a", p, 0.02, 0.1)], saved)
    assert second["a"]["step"] == 2
    assert torch.allclose(p, torch_reference(torch.tensor([1.0]), torch.tensor([0.25]), 0.02, 0.1, 2), atol=1e-7)


def test_input_state_is_not_mutated(submission):
    p = torch.tensor([1.0]); p.grad = torch.tensor([0.1])
    states = {"a": {"step": 1, "exp_avg": torch.tensor([0.2]), "exp_avg_sq": torch.tensor([0.3])}}
    before = copy.deepcopy(states)
    submission.grouped_adamw_step([group("a", p, 0.01, 0.0)], states)
    assert states["a"]["step"] == before["a"]["step"] and torch.equal(states["a"]["exp_avg"], before["a"]["exp_avg"])


def test_decoupled_weight_decay_with_zero_gradient(submission):
    p = torch.tensor([2.0]); p.grad = torch.zeros_like(p)
    submission.grouped_adamw_step([group("a", p, 0.1, 0.2)], {})
    assert torch.allclose(p, torch.tensor([1.96]))
