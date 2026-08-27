import copy
import pytest

torch = pytest.importorskip("torch")


def test_named_first_steps_match_torch_adam(submission):
    a = torch.tensor([1.0], dtype=torch.float64, requires_grad=True)
    b = torch.tensor([-2.0], dtype=torch.float64, requires_grad=True)
    a.grad, b.grad = torch.tensor([0.3], dtype=torch.float64), torch.tensor([-0.4], dtype=torch.float64)
    ref_a, ref_b = torch.nn.Parameter(a.detach().clone()), torch.nn.Parameter(b.detach().clone())
    ref_a.grad, ref_b.grad = a.grad.clone(), b.grad.clone()
    state = submission.named_adam_step({"a": a, "b": b}, {}, 0.02, 0.8, 0.95, 1e-7)
    torch.optim.Adam([ref_a, ref_b], lr=0.02, betas=(0.8, 0.95), eps=1e-7).step()
    assert torch.allclose(a, ref_a, atol=1e-8) and torch.allclose(b, ref_b, atol=1e-8)
    assert state["a"]["step"] == 1 and state["b"]["step"] == 1


def test_missing_gradient_preserves_existing_state(submission):
    p = torch.tensor([1.0], requires_grad=True)
    old = {"p": {"step": 3, "exp_avg": torch.tensor([0.2]), "exp_avg_sq": torch.tensor([0.4])}}
    state = submission.named_adam_step({"p": p}, old, 0.1)
    assert p.item() == 1.0 and state["p"]["step"] == 3
    assert torch.equal(state["p"]["exp_avg"], old["p"]["exp_avg"])


def test_missing_gradient_without_prior_state_stays_absent(submission):
    p = torch.tensor([1.0], requires_grad=True)
    assert submission.named_adam_step({"p": p}, {}, 0.1) == {}


def test_resume_matches_torch_for_multiple_steps(submission):
    p = torch.tensor([1.0], dtype=torch.float64, requires_grad=True); state = {}
    ref = torch.nn.Parameter(p.detach().clone()); opt = torch.optim.Adam([ref], lr=0.01, betas=(0.6, 0.9), eps=1e-6)
    for value in (0.2, -0.1, 0.5):
        gradient = torch.tensor([value], dtype=torch.float64)
        p.grad = gradient.clone(); ref.grad = gradient.clone()
        state = submission.named_adam_step({"p": p}, state, 0.01, 0.6, 0.9, 1e-6); opt.step()
    assert torch.allclose(p, ref, atol=1e-8) and state["p"]["step"] == 3


def test_input_state_and_gradients_are_not_mutated_or_aliased(submission):
    p = torch.tensor([1.0], requires_grad=True); p.grad = torch.tensor([0.5])
    old = {"p": {"step": 1, "exp_avg": torch.tensor([0.1]), "exp_avg_sq": torch.tensor([0.2])}}
    before, gradient = copy.deepcopy(old), p.grad.clone()
    state = submission.named_adam_step({"p": p}, old, 0.01)
    assert torch.equal(p.grad, gradient) and old["p"]["step"] == before["p"]["step"]
    assert state["p"] is not old["p"] and state["p"]["exp_avg"] is not old["p"]["exp_avg"]


def test_invalid_later_state_is_atomic(submission):
    a, b = torch.tensor([1.0], requires_grad=True), torch.tensor([2.0], requires_grad=True)
    a.grad, b.grad = torch.ones(1), torch.ones(1)
    invalid = {"b": {"step": 1, "exp_avg": torch.ones(2), "exp_avg_sq": torch.ones(2)}}
    with pytest.raises(ValueError):
        submission.named_adam_step({"a": a, "b": b}, invalid, 0.1)
    assert a.item() == 1.0 and b.item() == 2.0


@pytest.mark.parametrize("lr,beta1,beta2,eps", [(0.0, 0.9, 0.999, 1e-8), (0.1, 1.0, 0.999, 1e-8), (0.1, 0.9, 1.0, 1e-8), (0.1, 0.9, 0.999, 0.0)])
def test_invalid_hyperparameters_raise(submission, lr, beta1, beta2, eps):
    with pytest.raises(ValueError):
        submission.named_adam_step({"p": torch.ones(1)}, {}, lr, beta1, beta2, eps)
