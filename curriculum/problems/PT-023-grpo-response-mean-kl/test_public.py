import math
import pytest

torch = pytest.importorskip("torch")


def test_equal_rewards_no_kl(submission):
    x = torch.zeros(1, 3, 2)
    assert (
        submission.grpo_outcome_loss(
            torch.ones(1, 3), x, x, x, torch.ones_like(x, dtype=torch.bool)
        )
        == 0
    )


def test_equal_policy_reference_zero_kl(submission):
    x = torch.zeros(1, 2, 2)
    assert (
        submission.grpo_outcome_loss(
            torch.tensor([[0.0, 1.0]]),
            x,
            x,
            x,
            torch.ones_like(x, dtype=torch.bool),
            beta=0.2,
        )
        == 0
    )


def test_negative_advantage_clipping(submission):
    old = torch.zeros(1, 2, 1)
    new = torch.tensor([[[math.log(1.5)], [0.0]]])
    got = submission.grpo_outcome_loss(
        torch.tensor([[0.0, 1.0]]),
        new,
        old,
        new,
        torch.ones_like(old, dtype=torch.bool),
    )
    assert got.item() == pytest.approx(0.25, abs=1e-6)


def test_response_weight_not_token_weight(submission):
    old = torch.zeros(1, 2, 3)
    new = torch.tensor([[[math.log(1.5)] * 3, [0.0] * 3]])
    mask = torch.tensor([[[True, False, False], [True, True, True]]])
    got = submission.grpo_outcome_loss(torch.tensor([[0.0, 1.0]]), new, old, new, mask)
    assert got.item() == pytest.approx(0.25, abs=1e-6)


def test_empty_completion_rejected(submission):
    x = torch.zeros(1, 2, 2)
    with pytest.raises(ValueError):
        submission.grpo_outcome_loss(
            torch.ones(1, 2), x, x, x, torch.zeros_like(x, dtype=torch.bool)
        )


def test_padding_extremes_do_not_enter_ratios_or_gradients(submission):
    reward = torch.tensor([[0.0, 1.0]], dtype=torch.float64)
    new = torch.tensor(
        [[[0.0, 1000.0], [0.0, -1000.0]]], dtype=torch.float64, requires_grad=True
    )
    old = torch.zeros_like(new)
    mask = torch.tensor([[[True, False], [True, False]]])
    loss = submission.grpo_outcome_loss(reward, new, old, old, mask, beta=0.1)
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(new.grad).all()
    assert torch.equal(new.grad[~mask], torch.zeros(2, dtype=torch.float64))


def test_disabled_kl_does_not_evaluate_reference_exponential(submission):
    new = torch.zeros(1, 2, 1, dtype=torch.float64, requires_grad=True)
    ref = torch.full_like(new, 1000.0)
    loss = submission.grpo_outcome_loss(
        torch.ones(1, 2, dtype=torch.float64),
        new,
        new.detach(),
        ref,
        torch.ones_like(new, dtype=torch.bool),
        beta=0.0,
    )
    assert loss.item() == 0.0
