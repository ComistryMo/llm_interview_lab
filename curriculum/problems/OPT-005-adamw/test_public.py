import pytest

torch = pytest.importorskip("torch")


def test_first_step_decouples_weight_decay(submission):
    p = torch.tensor([2.0], dtype=torch.float64, requires_grad=True)
    p.grad = torch.tensor([1.0], dtype=torch.float64)
    state = submission.adamw_step([p], [None], 0.1, 0.9, 0.999, 1e-8, 0.2)[0]
    assert (
        torch.allclose(p, torch.tensor([1.86], dtype=torch.float64), atol=1e-8)
        and state["step"] == 1
    )


def test_zero_decay_matches_adam_formula(submission):
    p = torch.tensor([1.0], dtype=torch.float64, requires_grad=True)
    p.grad = torch.tensor([2.0], dtype=torch.float64)
    submission.adamw_step([p], [None], 0.01, 0.9, 0.999, 1e-8, 0.0)
    assert torch.allclose(p, torch.tensor([0.99], dtype=torch.float64), atol=1e-8)


def test_none_gradient_skips_decay_and_step(submission):
    p = torch.tensor([2.0], requires_grad=True)
    old = {"m": torch.zeros(1), "v": torch.zeros(1), "step": 4}
    state = submission.adamw_step([p], [old], 0.1, weight_decay=0.5)[0]
    assert p.item() == 2 and state["step"] == 4


def test_two_parameters_have_independent_state(submission):
    a = torch.tensor([1.0], requires_grad=True)
    b = torch.tensor([3.0], requires_grad=True)
    a.grad = torch.tensor([1.0])
    b.grad = torch.tensor([-1.0])
    states = submission.adamw_step([a, b], [None, None], 0.01, weight_decay=0.1)
    assert (
        len(states) == 2
        and states[0] is not states[1]
        and a.item() < 1
        and b.item() > 2.9
    )


@pytest.mark.parametrize("decay", [-1.0, float("inf"), True])
def test_invalid_weight_decay_raises_without_update(submission, decay):
    p = torch.tensor([1.0], requires_grad=True)
    p.grad = torch.tensor([1.0])
    with pytest.raises(ValueError):
        submission.adamw_step([p], [None], 0.1, weight_decay=decay)
    assert p.item() == 1


def test_checkpoint_state_resumes_the_same_trajectory(submission):
    continuous = torch.tensor([1.0, -2.0], dtype=torch.float64, requires_grad=True)
    continuous.grad = torch.tensor([0.3, -0.1], dtype=torch.float64)
    state = submission.adamw_step([continuous], [None], 0.01)[0]
    restored = continuous.detach().clone().requires_grad_()
    snapshot = {
        k: v.clone() if isinstance(v, torch.Tensor) else v for k, v in state.items()
    }
    before = {
        k: v.clone() if isinstance(v, torch.Tensor) else v for k, v in snapshot.items()
    }
    continuous.grad = torch.tensor([-0.2, 0.6], dtype=torch.float64)
    restored.grad = continuous.grad.clone()

    next_state = submission.adamw_step([continuous], [state], 0.01)[0]
    restored_state = submission.adamw_step([restored], [snapshot], 0.01)[0]

    assert torch.allclose(restored, continuous, atol=1e-12, rtol=1e-12)
    assert next_state["step"] == restored_state["step"] == 2
    for name in ("m", "v"):
        assert torch.equal(restored_state[name], next_state[name])
        assert torch.equal(snapshot[name], before[name])
    assert snapshot["step"] == before["step"] == 1
