import copy
import pytest

torch = pytest.importorskip("torch")


def test_named_parameters_update_with_independent_velocity(submission):
    a, b = torch.tensor([1.0], requires_grad=True), torch.tensor([2.0], requires_grad=True)
    a.grad, b.grad = torch.tensor([1.0]), torch.tensor([-2.0])
    state = submission.named_momentum_step({"a": a, "b": b}, {}, 0.1, 0.5)
    assert torch.allclose(a, torch.tensor([0.9])) and torch.allclose(b, torch.tensor([2.2]))
    assert torch.equal(state["a"], torch.tensor([1.0])) and torch.equal(state["b"], torch.tensor([-2.0]))


def test_missing_gradient_preserves_existing_state_and_parameter(submission):
    a, b = torch.tensor([1.0], requires_grad=True), torch.tensor([2.0], requires_grad=True)
    b.grad = torch.tensor([1.0])
    old = {"a": torch.tensor([3.0]), "b": torch.tensor([4.0])}
    state = submission.named_momentum_step({"a": a, "b": b}, old, 0.1, 0.5)
    assert a.item() == 1.0 and torch.equal(state["a"], old["a"])
    assert b.item() == pytest.approx(1.7) and torch.equal(state["b"], torch.tensor([3.0]))


def test_missing_gradient_without_prior_state_stays_absent(submission):
    p = torch.tensor([1.0], requires_grad=True)
    assert submission.named_momentum_step({"p": p}, {}, 0.1, 0.9) == {}


def test_input_state_and_gradients_are_not_mutated(submission):
    p = torch.tensor([1.0], requires_grad=True); p.grad = torch.tensor([0.5])
    old = {"p": torch.tensor([0.25])}; before = copy.deepcopy(old); gradient = p.grad.clone()
    state = submission.named_momentum_step({"p": p}, old, 0.1, 0.8)
    assert torch.equal(old["p"], before["p"]) and torch.equal(p.grad, gradient)
    assert state["p"] is not old["p"] and not state["p"].requires_grad


def test_resume_matches_torch_momentum(submission):
    p = torch.tensor([1.0], dtype=torch.float64, requires_grad=True); state = {}
    ref = torch.nn.Parameter(p.detach().clone()); opt = torch.optim.SGD([ref], lr=0.02, momentum=0.6)
    for value in (0.4, -0.2, 0.7):
        gradient = torch.tensor([value], dtype=torch.float64)
        p.grad = gradient.clone(); ref.grad = gradient.clone()
        state = submission.named_momentum_step({"p": p}, state, 0.02, 0.6); opt.step()
    assert torch.allclose(p, ref, atol=1e-8)


def test_invalid_later_state_does_not_partially_update(submission):
    a, b = torch.tensor([1.0], requires_grad=True), torch.tensor([2.0], requires_grad=True)
    a.grad, b.grad = torch.ones(1), torch.ones(1)
    with pytest.raises(ValueError):
        submission.named_momentum_step({"a": a, "b": b}, {"b": torch.ones(2)}, 0.1, 0.9)
    assert a.item() == 1.0 and b.item() == 2.0


@pytest.mark.parametrize("lr,momentum", [(0.0, 0.9), (0.1, -0.1), (0.1, 1.0)])
def test_invalid_hyperparameters_raise(submission, lr, momentum):
    with pytest.raises(ValueError):
        submission.named_momentum_step({"p": torch.ones(1)}, {}, lr, momentum)
